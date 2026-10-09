"""Require current native reports, independently exported netlist and file hashes."""
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from automation.kicad_tools.buck_model import build,EXAMPLE


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    root=EXAMPLE;cad=root/'kicad';evidence={}
    for kind in ('erc','drc'):
        latest=sorted((root/'verification').glob(f'*-{kind}-*/run.json'))[-1]
        manifest=json.loads(latest.read_text(encoding='utf8'))
        assert manifest['status']=='passed' and manifest['finding_count']==0,latest
        source=cad/('AIPE_Buck_1kW.kicad_sch' if kind=='erc' else 'AIPE_Buck_1kW.kicad_pcb')
        assert sha(source)==manifest['source_sha256'],f'{kind}: source changed'
        for name,digest in manifest['dependency_sha256'].items():assert sha(cad/name)==digest,(kind,name)
        evidence[kind]=dict(manifest=latest.relative_to(root).as_posix(),findings=0)
        shutil.copyfile(latest.parent/(kind+'.json'),root/'verification'/(kind.upper()+'_report.json'))
    output=root/'manufacturing';exports=json.loads((output/'export-manifest.json').read_text(encoding='utf8'))
    assert exports['status']=='passed' and len(exports['commands'])==11
    for name,digest in exports['input_sha256'].items():assert sha(cad/name)==digest,('export source changed',name)
    for name,record in exports['artifacts'].items():
        path=output/name;assert path.stat().st_size==record['bytes'] and sha(path)==record['sha256'],name
    tree=ET.parse(output/'netlist.xml').getroot()
    actual={(n.attrib['ref'],n.attrib['pin']):net.attrib['name'] for net in tree.findall('nets/net') for n in net.findall('node')}
    expected={(p['ref'],pin):net for p in build().parts for pin,net in p['nets'].items() if net}
    named={k:v for k,v in actual.items() if not v.startswith('unconnected-')}
    assert named==expected,('netlist mismatch',set(named.items())^set(expected.items()))
    assert {p['ref'] for p in build().parts}=={c.attrib['ref'] for c in tree.findall('components/comp')}
    metrics=json.loads((root/'verification/power-layout-metrics.json').read_text())
    assert metrics['board_sha256']==sha(cad/'AIPE_Buck_1kW.kicad_pcb')
    # Missing STEP models may still produce exit 0, so inspect the export log.
    step_log=(output/'logs/step.log').read_text(encoding='utf8')
    assert 'Could not add 3D model' not in step_log and 'File not found' not in step_log
    gerbers=[p for p in (output/'gerber').iterdir() if p.suffix!='.gbrjob']
    assert all(any(name in f.name.replace('-','_') for f in gerbers) for name in ('F_Cu','In1_Cu','In2_Cu','In3_Cu','In4_Cu','B_Cu'))
    evidence.update(status='passed',scope='CAD connectivity and export integrity only; hardware unqualified',
                    components=240,purchased_components=220,named_nets=len(set(expected.values())),mapped_pins=len(expected),
                    export_commands=11,export_files=len(exports['artifacts']),board_sha256=sha(cad/'AIPE_Buck_1kW.kicad_pcb'))
    (root/'verification/verification-summary.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence,indent=2))
    return evidence


if __name__=='__main__':verify()
