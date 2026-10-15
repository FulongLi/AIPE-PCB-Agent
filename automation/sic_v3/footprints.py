"""V3 manufacturer-dimensioned footprints; envelopes are not certified vendor CAD."""
from automation.kicad_tools.project_footprints import make_footprint, smd_pad, tht_pad, film_capacitor_footprint

BODY=(.22,.23,.25)

def isolated_so(name,n,pitch,row,padw,padh,bodyw,bodyh,height):
    pads=[]
    for i in range(n//2):
        y=(i-(n/2-1)/2)*pitch
        pads += [smd_pad(i+1,-row/2,y,padw,padh),smd_pad(n-i,row/2,y,padw,padh)]
    # Draw a complete courtyard around pad ends, not just the insulating body.
    ext=(row+padw)/2+.25
    extra=f'(fp_rect (start {-ext} {-bodyh/2-.25}) (end {ext} {bodyh/2+.25}) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))'
    text=make_footprint(name,'\n'.join(pads),bodyw,bodyh,
        'TI manufacturer land pattern; reinforced barrier copper spacing must also be checked after routing',name,
        courtyard_margin=.25,silkscreen=False)
    # Replace the body-only courtyard rather than leaving two overlapping contours.
    import re
    text=re.sub(r'\(fp_rect \(start [^\n]+\(layer "F.CrtYd"\)\)',lambda m:extra,text,count=1)
    return text,[(0,0,height/2+.1,bodyw,bodyh,height,BODY)]

def custom():
    f={}
    f['V3_UCC21710_HV']=isolated_so('V3_UCC21710_HV',16,1.27,9.75,1.65,.6,7.5,10.3,2.65)
    f['V3_UCC14141_DWN']=isolated_so('V3_UCC14141_DWN',36,.65,9.95,1.85,.45,7.5,12.83,2.65)
    f['V3_AMC1311_DWV']=isolated_so('V3_AMC1311_DWV',8,1.27,10.9,1.8,.6,7.5,5.85,2.8)
    for name,pitch,w,d,h,second in [('V3_CIN_15U',37.5,42,20,39.5,10.2),('V3_COUT_100U',52.5,57.5,35,50,20.3)]:
        f[name]=film_capacitor_footprint(name,pitch,w,d,h,1.4,pins=4,second_pitch_mm=second,pad_mm=3.4)
    name='V3_TO247_4'
    pads='\n'.join(tht_pad(i,x,0,(2.0,3.2),1.65,'oval') for i,x in enumerate([-5.08,0,2.54,5.08],1))
    text=make_footprint(name,pads,16.13,5.21,
       'C4MS025120K straight leads, 5.08/2.54/2.54 pitch; 1.65mm drill vs1.33x0.68mm lead. Manufacturing fit and insulated heatsink mounting require qualification',name,
       courtyard_margin=.5,silkscreen=False)
    f[name]=(text,[(0,0,17.815,16.13,5.21,23.63,BODY)])
    return f
