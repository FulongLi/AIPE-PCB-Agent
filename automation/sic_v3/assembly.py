"""Dimensioned V3 assembly envelopes and off-board procurement review list.

Boxes describe reserved volumes, not manufacturer solid models or validated
fit. Native PCB STEP models are exported separately from the completed PCBs.
"""
import csv,json,math
from pathlib import Path
from automation.sic_v3.model import EXAMPLE,HARNESS
from automation.sic_v3.calculations import magnetic
from automation.kicad_tools.simple_models import write_model
from automation.geometry.assembly_envelopes import screen


def generate():
    out=EXAMPLE/'mechanical';out.mkdir(exist_ok=True);parts=[]
    colors=dict(board=(.1,.45,.25),metal=(.65,.67,.7),copper=(.78,.4,.15),ceramic=(.9,.9,.85),body=(.25,.25,.3),plastic=(.55,.7,.85))
    def add(name,xyz,size,kind,evidence):
        parts.append(dict(name=name,centre_mm=xyz,size_mm=size,material_class=kind,evidence=evidence))
    add('PE baseplate',[180,142.5,-23.5],[470,455,3],'metal','Custom design envelope; top z=-22')
    add('Power PCB',[125,90,-1],[250,180,2],'board','Native board outline and specified stackup')
    add('Control PCB',[125,250,-1.2],[160,120,1.6],'board','Native board outline; origin (45,190,-0.4)')
    add('SK56 heatsink',[125,-21.755,110],[300,40,200],'metal','Manufacturer overall dimensions; fin geometry omitted')
    add('AlN unpunctured plate',[120,-1.205,23],[110,1,50],'ceramic','Custom design; solid insulation unqualified')
    for x in [105,130]:
        add('Live copper contact block '+str(x),[x,5.345,22],[16,12,14],'copper','Custom contact patch; vendor tab geometry/pressure pending')
        add('TO247 body '+str(x),[x,14,17.815],[16.13,5.21,23.63],'body','Package envelope only; body bottom z=6')
    add('PEEK pressure bar',[117.5,19,23],[65,5,12],'plastic','Custom clamp; creep, deflection and contact load unresolved')
    for x,y in [(6,6),(244,6),(6,174),(244,174),(49,194),(201,194),(49,306),(201,306)]:
        add('Insulating M3 support '+str((x,y)),[x,y,-12],[6,6,20],'plastic','Independent 20 mm support; fastener intrusion/creep pending')
    add('Wound choke reserve',[300,45,40.5],[80,80,85],'body','Custom four-core winding reserve, not a measured wound component')
    add('Choke insulating cradle',[300,45,-12],[90,90,20],'plastic','Separate chassis support; no PCB load')
    add('HO50 sensor reserve',[300,140,15.235],[45.19,40.8,34.47],'body','LEM horizontal-mount overall drawing; aperture and latch omitted')
    add('Sensor insulating pedestal',[300,140,-12],[50,45,20],'plastic','Separate chassis support')
    for tag,y in [('MAIN',230),('PRE',320)]:
        add('EV200 '+tag,[300,y,14.15],[80.48,58.19,72.3],'body','TE outline envelope; bottom at baseplate; terminals/covers approximate')
    add('HS100 precharge reserve',[365,140,-9.95],[47.5,88,24.1],'body','Manufacturer envelope, rotated 90 degrees; mounting face on PE plate')
    add('Fuse and cover reserve',[370,240,3],[30,95,50],'plastic','L60030M1C + SPL001 installation allowance, not a vendor solid')
    add('Auxiliary fuse and cover',[230,300,3],[30,95,50],'plastic','Separate KLKD008.T / L60030M1C / SPL001 installation reserve')
    add('80 mm fan',[125,-56.755,110],[80,25,80],'body','9GA0812P4G001 overall dimensions; duct not aerodynamically qualified')
    add('Power touch-guard reserve',[125,92.5,65],[260,185,2],'plastic','Front edge y=0 clears heatsink; nonconductive guard not credited as reinforced insulation')
    add('Choke touch-guard reserve',[300,47.5,95],[100,95,2],'plastic','Front edge y=0 clears heatsink; restrained wires; mechanical screening only')
    path=[(120.13,110.73,14),(120.13,110.73,32),(146.13,153,32),(146.13,195.73,32),(146.13,195.73,13.6)]
    length=sum(math.dist(a,b) for a,b in zip(path,path[1:]))
    dimensions=dict(baseplate_mm=[470,455,3],reserved_enclosure_internal_mm=[470,455,260],power_origin_mm=[0,0,0],control_origin_mm=[45,190,-.4],
        harness_centreline_mm=length,harness_finished_length_mm=160,harness_path_mm=path,harness_width_mm=50.8,
        notes=['Harness centreline is not its swept volume. Retention, bend, sag, connector engagement and full-width clearance require assembly review.',
               'The 470 x455 x260 mm enclosure is an installation reserve, not a compactness improvement claim.',
               'The SW terminal-to-choke centre distance is about 148 mm before lug and bend allowances; this external switching-node conductor adds EMI risk. Double-pulse/EMC measurements are mandatory.',
               'No automatic solid collision check can certify live-part clearance without exact vendor terminals, lugs and wire bends.'])
    payload=dict(status='ASSEMBLY DESIGN ENVELOPE — QUALIFICATION OPEN',dimensions=dimensions,parts=parts)
    (out/'assembly_envelope.json').write_text(json.dumps(payload,indent=2)+'\n')
    contacts={frozenset(('PEEK pressure bar','TO247 body '+str(x))):'0.105 mm overlapping clamp/body envelopes represent contact preload. Actual tab/body shape, pressure and PEEK creep remain unqualified.' for x in [105,130]}
    audit=screen(parts,contacts)
    (out/'envelope_interference_screen.json').write_text(json.dumps(audit,indent=2)+'\n')
    if audit['unexplained_intersections']:raise ValueError(audit['unexplained_intersections'])
    write_model(out/'models','v3_assembly_envelopes',[(*p['centre_mm'],*p['size_mm'],colors[p['material_class']]) for p in parts])
    # Top view, with scale and per-part labels; static engineering source SVG.
    from html import escape
    scale=2.;ox=150;oy=310
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1250" height="1200" viewBox="0 0 1250 1200">',
         '<rect width="1250" height="1200" fill="white"/>',
         '<g font-family="Arial,sans-serif" fill="#182936"><text x="40" y="40" font-size="26">V3 assembly installation reserve | top view</text>',
         '<text x="40" y="70" font-size="17">470 x 455 mm base | 260 mm reserved height | dimensions in mm</text>',
         '<text x="40" y="98" font-size="16">Envelope models only. No fabrication / energisation approval.</text>']
    shown=[p for p in parts if not any(w in p['name'] for w in ['support','contact block','TO247','pressure','touch-guard','cradle','pedestal','AlN'])]
    for p in shown:
        x,y,z=p['centre_mm'];w,h,d=p['size_mm'];color='#' + ''.join(f'{round(c*255):02x}' for c in colors[p['material_class']])
        svg.append(f'<rect x="{ox+(x-w/2)*scale:g}" y="{oy+(y-h/2)*scale:g}" width="{w*scale:g}" height="{h*scale:g}" fill="{color}" fill-opacity=".2" stroke="#425568" stroke-width="2"/>')
        label={'PE baseplate':'','HO50 sensor reserve':'HO50 sensor','HS100 precharge reserve':'HS100','Fuse and cover reserve':'HV fuse','Auxiliary fuse and cover':'Aux fuse'}.get(p['name'],p['name'])
        svg.append(f'<text x="{ox+x*scale:g}" y="{oy+y*scale:g}" text-anchor="middle" font-size="14">{escape(label)}</text>')
    svg.append('<polyline points="'+' '.join(f'{ox+x*scale},{oy+y*scale}' for x,y,z in path)+'" fill="none" stroke="#196cb4" stroke-width="5"/>')
    svg+=['<text x="40" y="1080" font-size="16">Blue: 40-way control harness centreline. Adjacent boards retain independent supports.</text>',
           '<text x="40" y="1108" font-size="16">Live copper blocks / ceramic / clamps require the separate thermal-interface review.</text>',
           '<text x="40" y="1136" font-size="16">Primary wiring, lugs, pressure duct, guard fasteners and cable motion remain assembly qualification inputs.</text></g></svg>']
    (out/'assembly_top.svg').write_text('\n'.join(svg),encoding='utf-8')
    rows=[
      ('K_MAIN K_PRE',2,'TE Connectivity','EV200HAANA','9–36 V coil; chassis mounted; NO auxiliary contact','https://www.te.com/en/product-1-1618002-8.html','DC interruption / fuse coordination and release time pending'),
      ('F_INPUT',1,'Littelfuse','KLKD020.T','20 A 600 VDC input fuse','https://www.littelfuse.com/assetdocs/solar-product-catalog?assetguid=c20b1154-026c-4f00-8409-f2a1fbf16baa','Conditional interrupting ratings; source fault energy coordination open'),
      ('F_AUX (system F2)',1,'Littelfuse','KLKD008.T','8 A 600 VDC coil/fan branch fuse','https://www.littelfuse.com/assetdocs/klkd-fuse-datasheet?assetguid=7b52eebb-c7cc-43df-a8da-9682a338e0f6','Inrush / ambient derating / current-limited source fault-clearing coordination pending'),
      ('FH_AUX',1,'Littelfuse','L60030M1C','Separate auxiliary fuse holder','https://www.littelfuse.com/assetdocs/class-cccd-10x38mm-datasheet?assetguid=a3e0f775-5259-4b6c-9260-49ad33f9c776','Separate location from HV input holder; wire and lug review'),
      ('COVER_AUX',1,'Littelfuse','SPL001','Auxiliary fuse-holder cover','https://www.littelfuse.com/assetdocs/class-cccd-10x38mm-datasheet?assetguid=a3e0f775-5259-4b6c-9260-49ad33f9c776','Assembly qualification pending'),
      ('FH_INPUT',1,'Littelfuse','L60030M1C','600 VAC/DC 30 A box-lug holder; 6–14 AWG copper; 4 N m','https://www.littelfuse.com/assetdocs/class-cccd-10x38mm-datasheet?assetguid=a3e0f775-5259-4b6c-9260-49ad33f9c776','Use SPL001 cover; actual dimensions and installed arc clearance review'),
      ('COVER_INPUT',1,'Littelfuse','SPL001','Fuse-holder touch cover','https://www.littelfuse.com/assetdocs/class-cccd-10x38mm-datasheet?assetguid=a3e0f775-5259-4b6c-9260-49ad33f9c776','Not an enclosure substitute'),
      ('R_PRE',1,'ARCOL / Ohmite','HS100 2K2 F','2.2 kOhm precharge; chassis thermal plate','https://media.digikey.com/pdf/Data%20Sheets/Ohmite%20PDFs/HS_Resistors.pdf','1 s fault pulse and restart temperature unqualified'),
      ('S_CURRENT',1,'LEM','HO 50-S-0100','Single insulated conductor through aperture; positive IP arrow towards output','https://www.lem.com/sites/default/files/products_datasheets/ho-50__250-s_v7.pdf','No bare busbar with panel mounting; exact signal harness below'),
      ('R_OCD_HARNESS',1,'Vishay','MRS25000C4701FCT00','4.7 kOhm pull-up at SENSOR END between pins 1 and 5','https://www.vishay.com/docs/28724/mrs16mrs25.pdf','Insulated harness assembly; cannot move pull-up to control PCB'),
      ('L_CHASSIS',1,'Custom','CUSTOM-4x0058192A2-28T-AWG10','Complete choke assembly; same L1 already listed off-board in power BOM','https://www.mag-inc.com/Media/Magnetics/Datasheets/0058192A2.pdf','Do not count twice; 4 cores and approximately %.3f m winding wire; insulation / temperature / bias test pending'%magnetic(25)['wire_length_m']),
      ('FAN',1,'Sanyo Denki','9GA0812P4G001','12 V 0.48 A; separately ducted; tach to control board','https://products.sanyodenki.com/en/sanace/dc/dc-fan/9GA0812P4G001/','Pressure operating point and exact PWM-open behavior to qualify'),
      ('TS_SINK',1,'Sensata','67L090P','NC limit; nominal 90 C, ±5 C; plastic bracket','https://www.sensata.com/sites/default/files/a/sensata-6700-series-subminiature-bimetal-disc-thermostats-datasheet.pdf','3.3 V /3.3 mA chain is below published 5 V/10 mA life condition; dry-contact reliability requires qualification'),
      ('TS_CHOKE',1,'Sensata','67L110P','NC limit; nominal 110 C, ±5 C; insulated external winding saddle','https://www.sensata.com/sites/default/files/a/sensata-6700-series-subminiature-bimetal-disc-thermostats-datasheet.pdf','Bracket test dielectric is not reinforced-system approval; thermal lag and dry-contact behavior open'),
      ('W_CTRL',1,'Custom using Samtec IDSD','40-way keyed, straight-through, 160 mm','Mates TST headers; gray 28 AWG cable; pin 1 preserved','https://suddendocs.samtec.com/catalog_english/idss.pdf','Final configured order code / length convention / strain relief to supplier review'),
      ('AUX_SOURCE',1,'Integration requirement','Isolated regulated 12 V /10 A','Independent lab auxiliary source; electronics branch and 8 A coil/fan fuse','', 'Source isolation, current-limit behavior, fusing and wire-drop qualification required'),
      ('PE_BOND',1,'Custom','Dedicated bolted protective-earth harness','Sink, chassis, precharge plate bonded; no PCB copper used as PE conductor','', 'Bond resistance / continuity and enclosure assembly test pending'),
      ('HV_WIRING',1,'Custom','10 AWG copper, >=600 V /105 C insulated','Power cabling; insulated lugs; conductor OD at sensor <=7.5 mm','', 'Cable ampacity, bend radius, termination temperature and 1 kV preferred insulation procurement check'),
      ('ESTOP',1,'Integration requirement','Maintained NC emergency-stop contact','Series with TS_SINK / TS_CHOKE in fail-open logic chain','', 'Not a certified emergency-stop safety function; exact contact rating / positive-opening hardware selection requires system safety review'),
    ]
    with (EXAMPLE/'components/bom_system.csv').open('w',newline='',encoding='utf8') as h:
        w=csv.writer(h);w.writerow(['reference','quantity','manufacturer','part_or_specification','function','source','qualification']);w.writerows(rows)
    (out/'control_harness.json').write_text(json.dumps(dict(finished_length_mm=160,pin_map=HARNESS,assembly_path_mm=path),indent=2)+'\n')
    print('Assembly envelopes, STEP, top view and off-board BOM written; qualification remains open.')

if __name__=='__main__':generate()
