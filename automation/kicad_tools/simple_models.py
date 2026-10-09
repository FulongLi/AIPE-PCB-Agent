"""Dimensioned envelope models for custom footprints; not vendor mechanical CAD.

Uses only the standard library. STEP faceted B-reps and VRML use the same boxes.
Threads, fuse cutouts, clamps, insulation and lead bends are deliberately absent.
"""
from pathlib import Path


def write_model(folder: Path, name: str, boxes):
    entities=[]
    def add(s):
        entities.append(s); return f'#{len(entities)}'
    app=add("APPLICATION_CONTEXT('automotive_design')")
    add(f"APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,{app})")
    pc=add(f"PRODUCT_CONTEXT('',{app},'mechanical')")
    product=add(f"PRODUCT('{name}','{name}','AIPE approximate dimensional envelope',({pc}))")
    formation=add(f"PRODUCT_DEFINITION_FORMATION('','',{product})")
    dc=add(f"PRODUCT_DEFINITION_CONTEXT('part definition',{app},'design')")
    definition=add(f"PRODUCT_DEFINITION('design','',{formation},{dc})")
    pds=add(f"PRODUCT_DEFINITION_SHAPE('','',{definition})")
    unit=add("(LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.))")
    rad=add("(NAMED_UNIT(*) PLANE_ANGLE_UNIT() SI_UNIT($,.RADIAN.))")
    solidangle=add("(NAMED_UNIT(*) SI_UNIT($,.STERADIAN.) SOLID_ANGLE_UNIT())")
    uncertainty=add(f"UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-6),{unit},'distance_accuracy_value','')")
    context=add(f"(GEOMETRIC_REPRESENTATION_CONTEXT(3) GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT(({uncertainty})) GLOBAL_UNIT_ASSIGNED_CONTEXT(({unit},{rad},{solidangle})) REPRESENTATION_CONTEXT('',''))")
    origin=add("CARTESIAN_POINT('',(0.,0.,0.))")
    axis=add(f"AXIS2_PLACEMENT_3D('',{origin},$,$)")
    solids=[]; vrml=['#VRML V2.0 utf8','# Approximate dimensional envelope, dimensions in mm.']
    faces=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))
    for x,y,z,w,d,h,color in boxes:
        vertices=[(x+xx*w/2,y+yy*d/2,z+zz*h/2) for xx,yy,zz in
                  [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        points=[add("CARTESIAN_POINT('',("+','.join(f'{v:.6f}' for v in xyz)+'))') for xyz in vertices]
        facet=[]
        for face in faces:
            loop=add("POLY_LOOP('',("+','.join(points[i] for i in face)+'))')
            bound=add(f"FACE_OUTER_BOUND('',{loop},.T.)")
            facet.append(add(f"FACE('',({bound}))"))
        shell=add("CLOSED_SHELL('',("+','.join(facet)+'))')
        solids.append(add(f"FACETED_BREP('{name}',{shell})"))
        rgb=' '.join(str(c) for c in color)
        # KiCad scales VRML model coordinates by 2.54.
        vrml.append(f'Transform {{ translation {x/2.54} {y/2.54} {z/2.54} children [ Shape {{ appearance Appearance {{ material Material {{ diffuseColor {rgb} }} }} geometry Box {{ size {w/2.54} {d/2.54} {h/2.54} }} }} ] }}')
    rep=add("FACETED_BREP_SHAPE_REPRESENTATION('',("+','.join([axis,*solids])+f'),{context})')
    add(f'SHAPE_DEFINITION_REPRESENTATION({pds},{rep})')
    folder.mkdir(parents=True,exist_ok=True)
    body='\n'.join(f'#{i}={s};' for i,s in enumerate(entities,1))
    (folder/(name+'.step')).write_text("ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('AIPE envelope model'),'2;1');\nFILE_NAME('"+name+"','2026-10-09T00:00:00',('AIPE'),('AIPE'),'AIPE','AIPE','');\nFILE_SCHEMA(('AUTOMOTIVE_DESIGN'));\nENDSEC;\nDATA;\n"+body+'\nENDSEC;\nEND-ISO-10303-21;\n')
    (folder/(name+'.wrl')).write_text('\n'.join(vrml)+'\n')


def generate(folder: Path):
    metal=(0.72,0.72,0.75);body=(0.22,0.23,0.25)
    write_model(folder,'IHXL2000VZ_10uH_Upright',[
        (0,0,29.4,50.8,21.59,50.8,body),
        (-16.255,0,1.5,7.11,2.01,5,metal),(16.255,0,1.5,7.11,2.01,5,metal)])
    write_model(folder,'CSS4J_4026_Kelvin',[
        (0,0,2.7,6.92,6.6,0.46,metal),
        (-4.025,0,0.215,2.01,6.6,0.43,metal),(4.025,0,0.215,2.01,6.6,0.43,metal),
        (-3.2,0,1.45,0.5,6.6,2.3,metal),(3.2,0,1.45,0.5,6.6,2.3,metal)])
    write_model(folder,'MIDI_70V_M6_P30',[(0,0,4,21,16,8,(0.3,0.4,0.8)),
        (-15,0,1,12,12,2,metal),(15,0,1,12,12,2,metal)])
    for name,w,d,h,pitch,n,ew,ed in [('TI_DDA8',3.9,4.9,1.5,1.27,4,2.71,3.4),('TI_PWP28',4.4,9.7,1.1,0.65,14,2.85,5.4)]:
        boxes=[(0,0,h/2+0.15,w,d,h,body),(0,0,0.075,ew,ed,0.15,metal)]
        boxes += [(side*(w/2+0.4),(i-(n-1)/2)*pitch,0.2,1.2,0.35,0.3,metal) for side in (-1,1) for i in range(n)]
        write_model(folder,name,boxes)
    write_model(folder,'ASV_7x5',[(0,0,0.95,7,5,1.5,(0.6,0.6,0.65))]+
                [(x,y,0.15,1.4,1.2,0.3,metal) for x in (-2.54,2.54) for y in (-1.27,1.27)])
