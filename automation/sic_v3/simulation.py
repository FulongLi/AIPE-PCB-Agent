"""Executed V3 behavioural models. No claimed device, thermal or hardware qualification.

Digital averaged control: nonlinear incremental inductance, current/voltage
sensor lags, 12-bit ADC, 1500-count PWM, saturation/anti-windup and one-cycle
actuation delay. Native ngspice independently evaluates switching ripple and
gate/DESAT networks. Parasitic values are sensitivity inputs, not extraction.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from scipy import signal
from automation.sic_v3.calculations import magnetic, gate_bias, FS
from automation.sic_v3.model import EXAMPLE
from automation.simulation.ngspice_runner import NgSpice
from automation.simulation.buck_stage import build_deck, resolve_params, analyse, write_svg_plot

OUT=EXAMPLE/'simulation'
TS=1/FS
CTRL=dict(kp_i=.015,ki_i=3.5,kp_v=.65,ki_v=400.,i_max=32.,d_max=.94,
          current_filter_s=3.74e-6,voltage_filter_s=12e-6,actuation_delay_cycles=1,
          adc_bits=12,pwm_counts=1500,deadtime_s=300e-9)

def save_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')

def averaged_case(name,*,vin=400,load=8,tend=.04,soft=False,load_step=None,vin_step=None,al=.92,cout=180e-6,dt=2e-6,quantize=True,switched=False):
    steps=int(round(tend/dt));stride=int(round(TS/dt))
    if not math.isclose(stride*dt,TS):raise ValueError('Integration step must divide the sample period')
    x=np.array([0.,0.,0.,0.,float(vin)]) if soft else np.array([200/load,200.,200/load,200.,float(vin)])
    vi=0. if soft else 200/load
    ii=0. if soft else .085*x[0]/vin
    applied=0. if soft else 200/vin+.015+ii
    pending=applied
    history=[]
    extrema=dict(i_max=float(x[0]),i_min=float(x[0]),v_max=float(x[1]),v_min=float(x[1]))
    def rhs(state,vsrc,res,duty,mode=None):
        i,v,fi,fv,fb=state
        l=magnetic(i,al_factor=al)['L_H']
        if mode is None:di=((max(0.,duty-.015)*vsrc)-v-.085*i-.138)/l
        else:
            vsw=vsrc-.068244*i if mode=='H' else -.068244*i if mode=='L' else -4.6 if i>0 else vsrc+4.6 if i<0 else v
            di=(vsw-v-.022*i)/l
        if duty<=0 and i<=0:di=max(0.,di)
        return np.array([di,(i-v/res)/cout,(i-fi)/CTRL['current_filter_s'],(v-fv)/CTRL['voltage_filter_s'],(vsrc-fb)/CTRL['voltage_filter_s']])
    for k in range(steps+1):
        t=k*dt;vsrc=vin if not vin_step or t<vin_step[0] else vin_step[1]
        res=load if not load_step or t<load_step[0] else load_step[1]
        ref=min(200.,1000*t) if soft else 200.
        if k%stride==0:
            fi,fv,fb=x[2],x[3],x[4]
            if quantize:
                fi=(np.clip(round((1.5+.032*fi)/3*4096),0,4095)*3/4096-1.5)/.032
                fv=np.clip(round(fv*(1.5/151)/3*4096),0,4095)*3/4096/(1.5/151)
                fb=np.clip(round(fb*(1.5/301)/3*4096),0,4095)*3/4096/(1.5/301)
            ev=ref-fv
            vi_candidate=vi+CTRL['ki_v']*TS*ev
            raw_i=CTRL['kp_v']*ev+vi_candidate
            target=float(np.clip(raw_i,0,CTRL['i_max']))
            if raw_i==target or (raw_i>target and ev<0) or (raw_i<target and ev>0):vi=vi_candidate
            ei=target-fi
            ii_candidate=ii+CTRL['ki_i']*TS*ei
            raw_d=fv/max(fb,300)+.015+CTRL['kp_i']*ei+ii_candidate
            command=float(np.clip(raw_d,0,CTRL['d_max']))
            if raw_d==command or (raw_d>command and ei<0) or (raw_d<command and ei>0):ii=ii_candidate
            if soft and ref<.5:command=0.
            if quantize:command=round(command*1500)/1500
            applied,pending=pending,command
            history.append([t,*x[:4],vsrc,res,ref,applied,target,x[4]])
        if k==steps:break
        cuts=[0.,dt]
        phase=(k%stride)*dt
        h_end=applied*TS/2
        l_start=h_end+CTRL['deadtime_s'];l_end=TS-h_end;h_start=l_end+CTRL['deadtime_s']
        if switched:
            cuts+= [edge-phase for edge in (h_end,l_start,l_end,h_start) if phase+1e-12<edge<phase+dt-1e-12]
        cuts=sorted(cuts)
        for left,right in zip(cuts,cuts[1:]):
            h=right-left;at=phase+(left+right)/2
            mode=None
            if switched:
                mode='D' if applied<=0 else 'H' if at<h_end or at>=h_start else 'L' if l_start<=at<l_end else 'D'
            old_i=x[0]
            a=rhs(x,vsrc,res,applied,mode);b=rhs(x+.5*h*a,vsrc,res,applied,mode)
            c=rhs(x+.5*h*b,vsrc,res,applied,mode);d=rhs(x+h*c,vsrc,res,applied,mode)
            x+=h*(a+2*b+2*c+d)/6
            if mode=='D' and old_i*x[0]<0:x[0]=0.
            extrema['i_max']=max(extrema['i_max'],float(x[0]));extrema['i_min']=min(extrema['i_min'],float(x[0]))
            extrema['v_max']=max(extrema['v_max'],float(x[1]));extrema['v_min']=min(extrema['v_min'],float(x[1]))
        if x[0]<0 and applied<=0:x[0]=0.
    data=np.asarray(history)
    folder=OUT/'results';folder.mkdir(parents=True,exist_ok=True)
    np.savetxt(folder/f'{name}.csv',data,delimiter=',',header='t_s,i_A,v_V,current_filtered_A,voltage_filtered_V,vin_V,load_ohm,reference_V,duty,current_reference_A,bus_filtered_V',comments='')
    late=data[:,0]>tend-.005
    result=dict(name=name,model='event-aligned switched behavioural; on-resistance/body-diode only' if switched else 'sampled averaged behavioural; no semiconductor switching or parasitics',dt_s=dt,
                mean_final_V=float(data[late,2].mean()),final_sampled_pkpk_V=float(np.ptp(data[late,2])),
                max_current_A=extrema['i_max'],min_current_A=extrema['i_min'],
                voltage_min_V=extrema['v_min'],voltage_max_V=extrema['v_max'],final_duty=float(data[-1,8]))
    event=load_step[0] if load_step else vin_step[0] if vin_step else .2 if soft else None
    if event is not None:
        after=data[data[:,0]>=event]
        err=np.abs(after[:,2]-200)
        bad=np.where(err>2)[0]
        result.update(event_time_s=event,max_deviation_V=float(err.max()),settle_1pct_s=float(after[bad[-1]+1,0]-event) if len(bad) and bad[-1]+1<len(after) else 0. if not len(bad) else None)
    return result,data

def margins(freq,response):
    db=20*np.log10(np.abs(response));phase=np.unwrap(np.angle(response))*180/np.pi
    crosses=np.where((db[:-1]>=0)&(db[1:]<0))[0]
    out=[]
    for j in crosses:
        w=db[j]/(db[j]-db[j+1]);fc=math.exp((1-w)*math.log(freq[j])+w*math.log(freq[j+1]))
        out.append(dict(crossover_Hz=fc,phase_margin_deg=float(180+(1-w)*phase[j]+w*phase[j+1])))
    gcross=np.where((phase[:-1]>-180)&(phase[1:]<=-180))[0]
    gm=[]
    for j in gcross:
        w=(phase[j]+180)/(phase[j]-phase[j+1]);gm.append(float(-((1-w)*db[j]+w*db[j+1])))
    return dict(gain_crossings=out,gain_margin_dB=min(gm) if gm else None)

def stability():
    freq=np.geomspace(1,24000,2400);z=np.exp(2j*np.pi*freq*TS)
    results=[];nominal=None
    for vin in [360,400,440]:
        for l in [348e-6,467e-6]:
            for cap in [180e-6,220e-6]:
                for load in [8.,16.]:
                    tf,tv=CTRL['current_filter_s'],CTRL['voltage_filter_s']
                    a=np.array([[-.085/l,-1/l,0,0],[1/cap,-1/(load*cap),0,0],[1/tf,0,-1/tf,0],[0,1/tv,0,-1/tv]])
                    b=np.array([[vin/l],[0],[0],[0]])
                    ad,bd,_,_,_=signal.cont2discrete((a,b,np.eye(4),np.zeros((4,1))),TS)
                    ai=np.zeros((6,6));bi=np.zeros((6,1));ci=np.zeros((1,6));ci[0,3]=1
                    ai[:4,:4]=ad;ai[:4,5]=bd[:,0]
                    ki,kp=CTRL['ki_i']*TS,CTRL['kp_i']
                    ai[4,4]=1;ai[4,2]=-ki;bi[4,0]=ki
                    ai[5,4]=1;ai[5,2]=-kp-ki;ai[5,3]=1/vin;bi[5,0]=kp+ki
                    plant=np.array([(ci@np.linalg.solve(zz*np.eye(6)-ai,bi))[0,0] for zz in z])
                    cv=CTRL['kp_v']+CTRL['ki_v']*TS/(1-1/z)
                    loop=plant*cv
                    av=np.zeros((7,7));av[:6,:6]=ai-bi@(ci*(CTRL['kp_v']+CTRL['ki_v']*TS))
                    av[:6,6]=bi[:,0];av[6,6]=1;av[6,:6]=-CTRL['ki_v']*TS*ci
                    eig=np.linalg.eigvals(av)
                    record=dict(vin_V=vin,L_H=l,C_F=cap,R_load_ohm=load,max_pole_magnitude=float(max(abs(eig))),
                                **margins(freq,loop))
                    results.append(record)
                    if vin==400 and l==348e-6 and cap==180e-6 and load==8:nominal=(freq,loop)
    save_json(OUT/'results/stability.json',dict(model='Exact ZOH linear plant, one sample command delay, two PI integrators, sensor lags; no saturation or quantisation in pole analysis',controller=CTRL,corners=results))
    return results,nominal

def switching(vin,duty):
    name=f'switching_{vin}'
    # Shared deck builder is generic; all V3 parameters are explicitly replaced.
    p=resolve_params(dict(name=name,vin=vin,vout_ref=200,fs=FS,closed_loop=False,duty=duty-.015,dead_time=CTRL['deadtime_s'],
         L=magnetic(28,al_factor=.92)['L_H'],L_dcr=magnetic(25)['Rdc_ohm'],Cout=180e-6,Cout_esr=.0043/2,
         Cin=54e-6,Cin_esr=.0091/4,L_in=10e-6,R_in=.08,Rds_on_hs=.033*(47/25)*1.1,Rds_on_ls=.033*(47/25)*1.1,
         body_diode_vf=4.6,body_diode_rs=.02,load_R=8.,t_end=.025,t_step=100e-9,metric_cycles=10,
         output=dict(csv_dt=100e-9,zoom_cycles=5,svg=False)))
    deck=build_deck(p)
    if isinstance(deck,str):deck=deck.splitlines()
    (OUT/'models').mkdir(parents=True,exist_ok=True)
    (OUT/'models'/f'{name}.cir').write_text('\n'.join(deck)+'\n',encoding='utf-8')
    ng=NgSpice();data=ng.run(deck,expected_end=p['t_end'])
    (OUT/'results'/f'{name}_ngspice.log').write_text('\n'.join(ng.messages),encoding='utf-8')
    result=analyse(p,data)
    result['digital_command_duty']=duty
    result['scope']='Open-loop steady-state switching cross-check; HS on-time reduced by300ns, both transitions have300ns dead time. The2ms open-loop ramp deliberately has no current controller and is NOT the V3 startup sequence; its overshoot/current are unsafe counterexample evidence. Simplified switch/diode model omits switching loss and Coss.'
    save_json(OUT/'results'/f'{name}_metrics.json',result)
    last=data['time']>p['t_end']-5/FS
    keys=['time','out','sw','l1#branch','duty']
    np.savetxt(OUT/'results'/f'{name}_zoom.csv',np.column_stack([data[k][last] for k in keys]),delimiter=',',header=','.join(keys),comments='')
    return result

def gate_and_desat():
    ng=NgSpice();bias=gate_bias();records=[]
    for cap in [680e-12*.95,680e-12*1.05]:
        deck=['V3 UCC21710 DESAT RC behavioural network; transistor survival not modelled',
              f'VDD vdd 0 {bias["positive_V"]}',
              'VDS drain 0 PWL(0 0 2u 0 2.02u 440 5u 440)',
              'VEN en 0 PULSE(0 1 1u 1n 1n 10u 20u)',
              'Boff off 0 V=1-v(en)',
              'Soff oc 0 off 0 clamp','.model clamp SW(Ron=2 Roff=1e12 Vt=.5 Vh=.01)',
              'Rtop vdd des 2.2k','Dhv des drain DHV','.model DHV D(Is=1e-10 N=1.7 Rs=.4 Cjo=15p Tt=75n Bv=1000)',
              'Rdiv des oc 9.09k','Rbot oc 0 1k',f'Cblank oc 0 {cap}',
              '.tran 1n 5u','.options method=gear reltol=1e-5','.end']
        data=ng.run(deck,expected_end=5e-6)
        for th in [.63,.7,.77]:
            hits=np.where((data['time']>=2e-6)&(data['oc']>=th))[0]
            latency=(data['time'][hits[0]]-2e-6) if len(hits) else None
            # C4 short-circuit withstand is NOT guaranteed. Include maximum driver
            # detection/soft turnoff estimates, rather than inventing an allowed time.
            records.append(dict(C_F=cap,threshold_V=th,rc_detect_s=float(latency) if latency is not None else None,
                                estimated_total_s=float(latency+.18e-6+.4e-6+156.25e-9/.25) if latency is not None else None))
        tag=f'desat_{cap:.4g}'
        (OUT/'models'/f'{tag}.cir').write_text('\n'.join(deck)+'\n',encoding='utf-8')
        (OUT/'results'/f'{tag}.log').write_text('\n'.join(ng.messages),encoding='utf-8')
        np.savetxt(OUT/'results'/f'{tag}.csv',np.column_stack([data[x] for x in ['time','drain','oc']]),delimiter=',',header='time,drain,oc',comments='')
    gates=[]
    for stray in [5e-9,15e-9,30e-9]:
        for dvdt in [20e9,50e9,100e9]:
            # Small-signal off-state Miller injection, conservatively use30nC/440V;
            # the active clamp is an assumed0.5ohm switch, not a vendor model.
            pulse=440/dvdt
            deck=['V3 off-state Miller susceptibility sensitivity, assumed parasitics',
                  f'Voff source 0 {bias["negative_V"]}','Roff source sink 5.9',f'Lgate sink g {stray}',
                  'Rclamp source g .5','Cgs g 0 3.087n',f'Iinj 0 g PULSE(0 {30e-9/440*dvdt} 100n 1n 1n {pulse} 1u)',
                  '.tran .2n 500n','.options method=gear reltol=1e-5','.end']
            data=ng.run(deck,expected_end=500e-9)
            tag=f'miller_{stray*1e9:g}nH_{dvdt/1e9:g}Vns'
            (OUT/'models'/f'{tag}.cir').write_text('\n'.join(deck)+'\n',encoding='utf-8')
            (OUT/'results'/f'{tag}.log').write_text('\n'.join(ng.messages),encoding='utf-8')
            gates.append(dict(assumed_L_H=stray,assumed_dvdt_V_s=dvdt,gate_peak_V=float(data['g'].max()),gate_min_V=float(data['g'].min())))
    return dict(ngspice=ng.version,desat=records,miller=gates,limitations=[
        'UF4007 diode parameters are a sensitivity approximation, not the manufacturer model.',
        'Clamp resistance, stray inductance and linearised Cgd are assumed; no extracted board parasitics.',
        'No C4MS025120K short-circuit survival time is guaranteed by its retrieved datasheet.',
        'The8us system-current shutdown target and driver timing at3.3V require measurement.'])

def fault_envelopes():
    """Conservative system-current target, not a device survival simulation.

    Shorted output, continuously on HS until target trip. The current sensor
    can under-read by2.4A; the assumed8us total target begins at40.4A true
    current. The guaranteed50% permeability point supplies a lower L bound.
    After inhibit, freewheel through the LS body diode plus winding resistance.
    This deliberately shows persistent output fault current after gate disable.
    """
    lmin=4*138e-9*.92*28**2*.5
    dt=20e-9;t=np.arange(0,400e-6+dt/2,dt);i=np.empty(len(t));i[0]=25.
    trip=None;off=None
    for k in range(1,len(t)):
        if trip is None and i[k-1]>=40.4:trip=t[k-1];off=trip+8e-6
        vin=440. if off is None or t[k-1]<off else -4.6
        i[k]=max(0.,i[k-1]+dt*(vin-.022*i[k-1])/lmin)
    result=dict(model='Constant minimum incremental L; bolted output short; worst continuously-on HS; assumed total8us delay after true40.4A; no MOSFET failure model',
        L_min_H=lmin,trip_threshold_true_A=40.4,assumed_delay_s=8e-6,
        threshold_time_s=float(trip),gate_inhibit_time_s=float(off),peak_A=float(i.max()),
        current_at_400us_A=float(i[-1]),inductor_energy_at_peak_J=float(.5*lmin*i.max()**2),
        output_cap_energy_at_200V_J=.5*220e-6*200**2,
        input_cap_energy_at_440V_J=.5*66e-6*440**2,
        limit='8us and sensor bandwidth over temperature are unqualified. Output capacitor fault discharge, fuse let-through, arc energy, DESAT survival and interruption require separate physical qualification.')
    np.savetxt(OUT/'results/system_fault.csv',np.column_stack([t,i]),delimiter=',',header='t_s,current_A',comments='')
    write_svg_plot(OUT/'results/system_fault.svg','Output short | assumed8us system target, minimum L',t,[('Inductor current',i)],'A')
    save_json(OUT/'results/system_fault.json',result)
    return result


def plots(cases,nominal):
    # Use the repository's tested scientific waveform renderer; no new software.
    for name,data in cases.items():
        scope='sampled event-aligned switching model' if name.startswith('switched_') else 'sampled averaged model'
        write_svg_plot(OUT/'results'/f'{name}.svg',name+' | '+scope,data[:,0],
                       [('Output',data[:,2]),('Reference',data[:,7])],'V')
    freq,loop=nominal
    for label,y,unit,ref in [('gain',20*np.log10(abs(loop)),'dB',0),('phase',np.unwrap(np.angle(loop))*180/np.pi,'degrees',-180)]:
        path=write_svg_plot(OUT/'results'/f'stability_{label}.svg','V3 outer loop | ZOH + one-cycle delay + sensor lags',
                           np.log10(freq),[(label,y)],unit,x_unit='s',reference=ref)
        path.write_text(path.read_text(encoding='utf-8').replace('time / s','log10(frequency / Hz)'),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['control','spice','all'],default='all');args=ap.parse_args()
    (OUT/'results').mkdir(parents=True,exist_ok=True);(OUT/'models').mkdir(exist_ok=True)
    if args.stage in ['control','all']:
        cases={};summary=[]
        requests=[('startup',dict(soft=True,tend=.24)),('load_up',dict(load=16,load_step=(.01,8))),
                  ('load_down',dict(load=8,load_step=(.01,16))),('input_step',dict(vin=360,vin_step=(.01,440)))]
        for name,kw in requests:
            result,data=averaged_case(name,**kw);summary.append(result);cases[name]=data
            print(name,json.dumps(result),flush=True)
        for name,kw in requests:
            result,data=averaged_case('switched_'+name,switched=True,**kw);summary.append(result);cases['switched_'+name]=data
            print(result['name'],json.dumps(result),flush=True)
        for v in [360,400,440]:
            result,_=averaged_case(f'corner_{v}',vin=v);summary.append(result)
        # Numerical check of nonlinear transients at half integration step.
        fine,_=averaged_case('load_up_dt1us',load=16,load_step=(.01,8),dt=1e-6)
        coarse=next(r for r in summary if r['name']=='load_up')
        convergence=dict(coarse_dt_s=2e-6,fine_dt_s=1e-6,max_deviation_difference_V=abs(fine['max_deviation_V']-coarse['max_deviation_V']))
        stability_results,nominal=stability()
        plots(cases,nominal)
        save_json(OUT/'results/control_summary.json',dict(controller=CTRL,cases=summary,convergence=convergence,
            max_discrete_pole=max(r['max_pole_magnitude'] for r in stability_results),
            min_phase_margin_deg=min(c['phase_margin_deg'] for r in stability_results for c in r['gain_crossings'])))
    if args.stage in ['spice','all']:
        control=json.loads((OUT/'results/control_summary.json').read_text())
        for v in [360,400,440]:
            duty=next(c['final_duty'] for c in control['cases'] if c['name']==f'corner_{v}')
            result=switching(v,duty);print('switching',v,result,flush=True)
        save_json(OUT/'results/gate_fault.json',gate_and_desat())
        fault_envelopes()
    sources=[Path(__file__),Path(__file__).with_name('calculations.py'),Path(__file__).with_name('model.py'),
             Path('automation/simulation/buck_stage.py'),Path('automation/simulation/ngspice_runner.py')]
    save_json(OUT/'results/provenance.json',dict(source_sha256={str(p).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        controller=CTRL,model_limits='Behavioural models only; no vendor SiC nonlinear model, loss/EMC/insulation qualification or hardware timing claim'))

if __name__=='__main__':main()
