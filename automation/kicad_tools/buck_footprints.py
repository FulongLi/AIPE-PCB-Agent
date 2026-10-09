"""Vendor-library subset plus dimensioned project-specific power footprints."""
from __future__ import annotations

import os
import shutil
import re
from pathlib import Path

from automation.kicad_tools.buck_model import build, EXAMPLE
from automation.setup.detect_kicad import find_kicad_cli


def data_root():
    cli=find_kicad_cli()
    return Path(os.environ.get('AIPE_KICAD_DATA',str(cli.parent.parent/'share/kicad')))


def footprint(name, pads, width, height, description):
    return f'''(footprint "{name}" (version 20260206) (generator "aipe") (layer "F.Cu")
      (descr "{description}")
      (property "Reference" "REF**" (at 0 {-height/2-2} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
      (property "Value" "{name}" (at 0 {height/2+2} 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
      (fp_rect (start {-width/2} {-height/2}) (end {width/2} {height/2}) (stroke (width 0.15) (type default)) (fill none) (layer "F.Fab"))
      (fp_rect (start {-width/2-0.5} {-height/2-0.5}) (end {width/2+0.5} {height/2+0.5}) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))
      {pads}
      (model "${{KIPRJMOD}}/libraries/AIPE.3dshapes/{name}.wrl"
        (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))
    )\n'''


def prepare():
    source=data_root()
    target=EXAMPLE/'kicad/libraries'
    target.mkdir(parents=True,exist_ok=True)
    from automation.kicad_tools.simple_models import generate
    generate(target/'AIPE.3dshapes')
    libs=set()
    for p in build().parts:
        lib,name=p['footprint'].split(':');libs.add(lib)
        dst=target/(lib+'.pretty');dst.mkdir(exist_ok=True)
        if lib=='AIPE':continue
        original=source/'footprints'/(lib+'.pretty')/(name+'.kicad_mod')
        if not original.exists():raise FileNotFoundError(original)
        shutil.copyfile(original,dst/original.name)
        replacement='TI_DDA8' if p['ref'] in ('U1','U2') else 'TI_PWP28' if p['ref']=='U4' else 'ASV_7x5' if p['ref']=='Y1' else None
        if replacement:
            file=dst/original.name
            text=file.read_text(encoding='utf8')
            text=re.sub(r'\(model "[^"]+"',f'(model "${{KIPRJMOD}}/libraries/AIPE.3dshapes/{replacement}.wrl"',text)
            file.write_text(text,encoding='utf8')
    custom=target/'AIPE.pretty'
    # 10 uH Figure B: 25.4 inner-edge gap + 7.11 lead width = 32.51 center pitch.
    pads='\n'.join(f'''(pad "{i+1}" thru_hole oval (at {x} 0) (size 12 7)
        (drill oval 8.5 3.0) (layers "*.Cu" "*.Mask") (remove_unused_layers no))''' for i,x in enumerate((-16.255,16.255)))
    (custom/'IHXL2000VZ_10uH_Upright.kicad_mod').write_text(footprint('IHXL2000VZ_10uH_Upright',pads,51.1,21.97,
        'Vishay 34681 Fig B; upright lead-axis mounting; slots 8.5x3.0; pitch 32.51; independent clamp required'))
    # Force pads: x +/-4.025, 2.55 x 5.6. Sense pads: same x, 2.55 x 0.9.
    pads=[]
    for n,x,y,w,h in [(1,-4.025,0.85,2.55,5.6),(2,4.025,0.85,2.55,5.6),(3,-4.025,-3.2,2.55,0.9),(4,4.025,-3.2,2.55,0.9)]:
        pads.append(f'(pad "{n}" smd rect (at {x} {y}) (size {w} {h}) (layers "F.Cu" "F.Paste" "F.Mask"))')
    (custom/'CSS4J_4026_Kelvin.kicad_mod').write_text(footprint('CSS4J_4026_Kelvin','\n'.join(pads),10.6,7.3,
        'Bourns CSS4J-4026 recommended pads; left force 1 sense 3; right force 2 sense 4; do not short Kelvin pads on PCB'))
    pads='\n'.join(f'(pad "{i+1}" thru_hole circle (at {x} 0) (size 12 12) (drill 6.5) (layers "*.Cu" "*.Mask") (remove_unused_layers no))' for i,x in enumerate((-15,15)))
    (custom/'MIDI_70V_M6_P30.kicad_mod').write_text(footprint('MIDI_70V_M6_P30',pads,42,16,
        'Littelfuse 4998 MIDI 70 V; 30 mm center pitch; M6 bolt assembly; insulating mechanical support required'))
    table=['(fp_lib_table (version 7)']
    for lib in sorted(libs):
        table.append(f'(lib (name "{lib}") (type "KiCad") (uri "${{KIPRJMOD}}/libraries/{lib}.pretty") (options "") (descr "V1 project library"))')
    (EXAMPLE/'kicad/fp-lib-table').write_text('\n'.join(table)+')\n')
    # Preserve official licensing of copied KiCad library material.
    notices=ROOT_SMOKE=EXAMPLE.parents[0]/'automation-smoke/kicad/libraries'
    for name in ('LICENSE.md','CC-BY-SA-4.0.txt'):
        original=notices/name
        if original.exists():shutil.copyfile(original,target/name)
    (target/'NOTICE.md').write_text('''# Library provenance

Stock copper/pad geometry comes from the official KiCad 10.0.7 library. U1/U2,
U4 and Y1 have only their missing model reference replaced by a dimensioned AIPE
envelope. They retain the KiCad library license; see the accompanying license.
Custom AIPE symbols and footprints were generated from the manufacturer drawings
identified in descriptions and components/references.json. No proprietary CAD
library was imported. Three custom power footprints require independent dimensional
review; a passing DRC cannot establish vendor package compatibility.
''')
    print(f'Prepared {len(libs)} project footprint libraries.')


if __name__=='__main__':prepare()
