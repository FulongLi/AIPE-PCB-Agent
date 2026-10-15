"""Repair obsolete KiCad model paths without changing any copper geometry.

TPS767D301 PWP body uses the maximum package envelope, not a vendor solid.
Its exposed-pad and leads remain defined by the editable footprint, not this
visual model. Native DRC/parity and manufacturing exports must be refreshed.
"""
from pathlib import Path
from automation.sic_v3.model import EXAMPLE
from automation.kicad_tools.simple_models import write_model


def main():
    root=EXAMPLE/'kicad/control_board'
    write_model(root/'models','V3_PWP28_BODY_APPROX',[(0,0,.7,4.5,9.8,1.2,(.22,.23,.25))])
    replacements={
        '${KICAD10_3DMODEL_DIR}/Package_SO.3dshapes/TSSOP-16-1EP_4.4x5mm_Pitch0.65mm_EP3.4x5mm.step':
        '${KICAD10_3DMODEL_DIR}/Package_SO.3dshapes/HTSSOP-16-1EP_4.4x5mm_P0.65mm_EP3.4x5mm.step',
        '${KICAD10_3DMODEL_DIR}/Package_SO.3dshapes/HTSSOP-28-1EP_4.4x9.7mm_P0.65mm_EP2.85x5.4mm.step':
        '${KIPRJMOD}/models/V3_PWP28_BODY_APPROX.step',
        '${KICAD10_3DMODEL_DIR}/Oscillator.3dshapes/Oscillator_SMD_SeikoEpson_SG8002CA-4Pin_7.0x5.0mm.step':
        '${KICAD10_3DMODEL_DIR}/Oscillator.3dshapes/Oscillator_SMD_Abracon_ASV-4Pin_7.0x5.1mm.step',
    }
    for path in [root/'sic-v3-control.kicad_pcb',*root.glob('libraries/**/*.kicad_mod')]:
        old=path.read_bytes();new=old
        for a,b in replacements.items():new=new.replace(a.encode(),b.encode())
        if new!=old:path.write_bytes(new)


if __name__=='__main__':main()
