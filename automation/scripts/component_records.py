"""Add explicit operating stress and manufacturer-based selection rationale."""
import csv
import json
from automation.kicad_tools.buck_model import build,EXAMPLE


def generate():
    refs={s['id']:s['url'] for s in json.loads((EXAMPLE/'components/references.json').read_text())['sources']}
    # Ratings are conditional on the linked data-sheet test conditions; operating
    # stresses are engineering calculations, not measurement results.
    selected={
      'CSD19536KCS':('100 V VDS; +/-20 V VGS','100 A package limit; silicon rating is not a PCB current rating','Rds(on) max 2.7 mohm at VGS=10 V; Tj max 175 C','Qg 153 nC upper budget; switching transition is an unverified 100 ns total scenario','54 V DC; 52.08 A inductor peak shared by two devices; 12 V gate','46 V static VDS headroom; overshoot and current sharing unverified','Low resistance; through-hole insulated heatsinking'),
      'IHXL2000VZEB100M3A':('Winding insulation requires vendor application review','83 A heat-rise rating and 83 A at 20% L drop','DCR max 0.86 mohm; 40 C rise at rated thermal current; core-loss budget 4 W unverified','10 uH +/-20%; nonlinear inductance; 100 kHz design','41.84 Arms; 52.08 A scenario peak; 60 A trip','Peak is 63% of 83 A; no guaranteed short-circuit survival','High-current magnetic; independent mechanical support'),
      'CSS4J-4026K-2L00F':('Resistance element; voltage rating not limiting here','6 W with 70 C terminal-temperature condition','2 mohm +/-1%; full-load loss 3.50 W','Four distinct force/sense terminals','83.3 mV nominal drop; 3.50 W at full load','58% of 6 W; 60 A gives 7.2 W and must trip','Kelvin measurement after inductor'),
      'EKY-101ELL471MM25S':('100 V','1.75 Arms at 105 C / 100 kHz per capacitor','36 mohm max impedance at 20 C, used only as ESR proxy','470 uF +/-20%; no lifetime guarantee from this budget','54 V; total bank 20.98 Arms worst calculated','54% voltage utilization; 24.5/20.98=1.17 ripple rating ratio before sharing/temperature','Fourteen parallel capacitors for input RMS ripple'),
      'EKY-500ELL102ML25S':('50 V','2.555 Arms at 105 C / 100 kHz per capacitor','25 mohm max impedance used as ESR proxy','1000 uF +/-20%','24 V nominal / 27.5 V fault threshold; bank ripple 6.01 Arms','10.22/6.01=1.70 ripple ratio; 55% rated voltage at threshold','Four parallel output capacitors'),
      'UCC27211DDAR':('120 V bootstrap rating; 8-17 V recommended VDD','4 A peak source/sink class; transient, not average','Exposed pad tied to ground; five thermal vias','Independent HI/LI; bootstrap; no internal deadtime guarantee','12 V supply; two 153 nC gates per output at 100 kHz','0.734 W upper total gate-energy budget; edge timing unverified','High-current independent half-bridge driver'),
      'LM5164DDAR':('6-100 V input','1 A output rating','Exposed pad with five thermal vias; dissipation must be checked in system','COT with manufacturer ripple-injection network','36-54 V to 12 V; estimated auxiliary input 4.5 W','54% maximum input-voltage rating; budget below 1 A output','Wide-input integrated auxiliary buck'),
      'TPS54302DDCR':('4.5-28 V input','3 A output rating','SOT-23-6; thermal/current capability depends on layout','400 kHz internally compensated buck','12 V to approximately 5 V; loads budgeted below 1 A','12/28 input utilization; substantial DC current margin','Compact second auxiliary stage'),
      'TPS767D301PWPR':('2.7-10 V input','1 A per output conditional on thermal limits','1.58 W estimated dissipation; nine EP vias; datasheet test-board RthetaJA is not guaranteed here','Adjustable core channel / fixed 3.3 V I/O; delayed open-drain resets','5 V to 1.899 V at 0.4 A and 3.3 V at 0.2 A budgets','Current budgets 40% and 20%; combined package thermal limit controls','Core-first sequencing using regulator reset and NPN'),
      'TMS320F28335PGFA':('1.9 V core at 150 MHz; 3.3 V I/O; ADC 0-3 V full scale','0.4 A core / 0.2 A I/O are design budgets, not part maxima','Power and temperature depend on enabled peripherals','150 MHz target; 30 MHz oscillator; ePWM deadband required','Nominal core 1.899 V; input ADC <=2.139 V at 54 V','ADC headroom 0.861 V at maximum continuous input; supply tolerances require validation','User-preferred DSP with full 176-pin mapping'),
      'INA240A1DR':('Common-mode -4 to 80 V; 2.7-5.5 V supply','Voltage-output current-sense amplifier','Offset/gain drift and shunt temperature require calibration','20 V/V gain; bandwidth/delay not suitable evidence of hard-short protection','24 V common mode; 3.3 V supply; 1.667 V output at full load','2.4 V at 60 A trip; positive-current-only design','PWM rejection and true Kelvin sensing'),
      '74651195':('Insulation/system clearance reviewed separately','85 A at 20 C vendor condition','M5; load depends on PCB, cable and torque','Nine solder pins','41.67 A output / <30 A input continuous budget','Output is 49% of vendor 20 C current condition; no hot derating qualification','Bolted cable connection with soldered high-current pins'),
      '4998040.M-NH':('70 V DC','40 A nominal fuse rating','Temperature derating, breaking capacity and I2t require source-system review','Time-current fuse; cannot protect MOSFET in microseconds','<30 A input budget at 36 V; 6.58 mF input capacitance','54/70 voltage utilization; inrush/hotplug not qualified','Sustained fault isolation in current-limited bench scope'),
      'SMCJ54A-13-F':('54 V standoff; 87.1 V stated pulse clamp','1500 W pulse class, not sustained power','Pulse rating follows specified waveform','Unidirectional TVS; cathode VIN','54 V maximum continuous input assumption','100-87.1=12.9 V nominal device headroom at stated clamp test; wiring overshoot unverified','Local transient clamp; not a surge compliance claim'),
    }
    fields=['reference','manufacturer','part_number','package','voltage_rating','current_rating','thermal_characteristics','switching_parameters','operating_stress','engineering_margin','selection_reason','datasheet','verification_limit']
    with (EXAMPLE/'components/component_selection.csv').open('w',newline='',encoding='utf8') as f:
        out=csv.DictWriter(f,fieldnames=fields);out.writeheader()
        for p in build().parts:
            if p['kind'] in ('TP','H'):continue
            spec=selected.get(p['mpn'])
            if spec is None:
                if p['kind']=='R':
                    spec=('150 V RC0805 / 200 V RC2512 working-voltage class','Limited by resistance and power','0.125 W RC0805 / 1 W RC2512 at rating conditions','1% thick-film','See connected rail and resistor value; dividers <25 mW; bleeders <=0.292 W','Bleeders below 30% of 1 W; series-gate pulse qualification still required','Standard-value resistor')
                elif p['kind']=='C':
                    rating=p['value'].split('/')[-1]
                    spec=(rating,'Ceramic ripple capability application dependent','DC bias/temperature/ESR require exact MPN data','Nominal value is not effective biased capacitance','See rail in circuit.json; bootstrap 12 V; rail bypass <=54 V','Nominal voltage exceeds connected DC rail; effective-capacitance margin unverified','Bypass, filtering or hold-up per schematic')
                else:
                    spec=('See manufacturer data sheet','See manufacturer data sheet','Application temperature/derating unverified','Pin functions checked in electrical model','See circuit.json and calculations.md','No numeric margin asserted','Required supply, protection, sensing or debug function')
            out.writerow(dict(zip(fields,[p['ref'],p['maker'],p['mpn'],p['footprint'],*spec,refs.get(p['source'],p['source']),'No procurement/lot/availability or hardware qualification; independent BOM review required'])))
    with (EXAMPLE/'components/bom.csv').open('w',newline='',encoding='utf8') as f:
        out=csv.writer(f);out.writerow(['Reference','Value','Manufacturer','MPN','Footprint','Datasheet','Assembly note'])
        for p in build().parts:
            if p['kind'] not in ('TP','H'):out.writerow([p['ref'],p['value'],p['maker'],p['mpn'],p['footprint'],refs.get(p['source'],p['source']),p['note']])


if __name__=='__main__':generate()
