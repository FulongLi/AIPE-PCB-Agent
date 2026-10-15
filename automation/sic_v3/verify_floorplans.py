"""Preserve native pre-routing checks without presenting them as a routed gate."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,subprocess
from collections import Counter
from automation.sic_v3.model import EXAMPLE,ROOT
from automation.setup.detect_kicad import find_kicad_cli


def main():
    folder=EXAMPLE/'verification/floorplan';folder.mkdir(parents=True,exist_ok=True)
    cli=find_kicad_cli();summary={}
    for label,relative,parity in [('power_A','kicad/power_board/sic-v3-power-A.kicad_pcb',False),
                                  ('power_B','kicad/power_board/sic-v3-power.kicad_pcb',True),
                                  ('control','kicad/control_board/sic-v3-control.kicad_pcb',True)]:
        board=EXAMPLE/relative;output=folder/(label+'.json')
        cmd=[str(cli),'pcb','drc','--format','json','--severity-all','--output',str(output)]
        if parity:cmd.append('--schematic-parity')
        cmd.append(str(board))
        run=subprocess.run(cmd,capture_output=True)
        (folder/(label+'.stdout.log')).write_bytes(run.stdout);(folder/(label+'.stderr.log')).write_bytes(run.stderr)
        data=json.loads(output.read_text(encoding='utf-8-sig'))
        summary[label]=dict(board=relative,board_sha256=hashlib.sha256(board.read_bytes()).hexdigest(),
            report=str(output.relative_to(EXAMPLE)).replace('\\','/'),tool_exit=run.returncode,
            command=cmd,violations=len(data.get('violations',[])),by_type=dict(Counter(v['type'] for v in data.get('violations',[]))),
            reported_unconnected_items=len(data.get('unconnected_items',[])),parity_checked=parity,
            parity_findings=len(data.get('schematic_parity',[])))
    record=dict(purpose='Footprint/placement-only gate before routing; unconnected-item list may reach native report limit; never a routed CAD pass',
        generated_utc=datetime.now(timezone.utc).isoformat(),native_version=subprocess.check_output([str(cli),'version'],text=True).strip(),checks=summary)
    (folder/'manifest.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print({k:{x:v[x] for x in ['violations','reported_unconnected_items','parity_findings']} for k,v in summary.items()})
    if any(v['tool_exit'] or v['violations'] or v['parity_findings'] for v in summary.values()):raise SystemExit(1)

if __name__=='__main__':main()
