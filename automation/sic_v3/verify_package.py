"""Verify V3 netlist equality and freshness of the frozen review evidence.

netlists uses KiCad Python; evidence uses the host numerical environment.
This validates review artifacts, never approves hardware release.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from automation.sic_v3.model import EXAMPLE


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def netlists():
    from automation.verification.netlist_check_sic import load_xml,load_board,compare
    out=[]
    for which in ['power','control']:
        m=EXAMPLE/f'design/circuit_{which}.json';parts=read(m)
        expected={(p['ref'],str(k)):v for p in parts for k,v in p['nets'].items() if v}
        refs={p['ref'] for p in parts};onboard={p['ref'] for p in parts if p.get('on_board',True)}
        xml=EXAMPLE/f'manufacturing/{which}/netlist.xml';board=EXAMPLE/f'kicad/{which}_board/sic-v3-{which}.kicad_pcb'
        a,ar,ai,ad=load_xml(xml);b,br,bi,bd=load_board(board.resolve())
        sm=compare(a,expected,'schematic','model',ar,refs)
        bm=compare(b,{k:v for k,v in expected.items() if k[0] in onboard},'board','model',br,onboard)
        row=dict(board=which,inputs={str(p.relative_to(EXAMPLE)):sha(p) for p in [m,xml,board]},schematic_vs_model=sm,board_vs_model=bm,
                 schematic_info=ai,board_info=bi,duplicate_nodes=ad,conflicting_pads=bd,offboard_refs=sorted(refs-onboard))
        row['passed']=sm['exact'] and bm['exact'] and not ad and not bd;out.append(row)
        print(which,row['passed'],sm['mismatches'],bm['mismatches'])
    p=EXAMPLE/'verification/circuit_checks/netlist_equality.json';p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(out,indent=2)+'\n')
    if not all(r['passed'] for r in out):raise SystemExit(1)


def evidence():
    findings=[];checks={};inputs={}
    def check(name,passed,detail=None):
        checks[name]=dict(passed=bool(passed),detail=detail)
        if not passed:findings.append(name)
    def record(p):inputs[p.relative_to(EXAMPLE).as_posix()]=sha(p)
    n=EXAMPLE/'verification/circuit_checks/netlist_equality.json';record(n)
    for row in read(n):
        check(row['board']+'_model_netlist',row['passed'] and all(sha(EXAMPLE/p)==h for p,h in row['inputs'].items()))
    for which in ['power','control']:
        board=EXAMPLE/f'kicad/{which}_board/sic-v3-{which}.kicad_pcb';record(board)
        p=EXAMPLE/f'verification/drc/{which}.json';d=read(p);record(p)
        m=read(EXAMPLE/f'pcb/routing_analysis/{which}_native_completion.json')
        check(which+'_native_drc',not any(d[k] for k in ['violations','unconnected_items','schematic_parity']) and m['board_sha256']==sha(board) and m['report_sha256']==sha(p),d['ignored_checks'])
        root=EXAMPLE/f'manufacturing/{which}';p=root/'export-manifest.json';m=read(p);record(p)
        stale=[a for a,v in m['artifacts'].items() if sha(root/a)!=v['sha256']]
        stale += [a for a,h in m['input_sha256'].items() if sha(board.parent/a)!=h]
        check(which+'_native_exports',m['status']=='passed' and not stale,stale)
        p=EXAMPLE/f'verification/engineering_checks/{which}_copper_islands.json';d=read(p);record(p)
        check(which+'_copper_islands',d['board_sha256']==sha(board) and all(v['component_count']==1 for v in d['nets']))
    for which,folder in [('power','power_board'),('control','control_board'),('system','system_wiring')]:
        runs=[]
        for p in sorted((EXAMPLE/'verification/erc').glob('*/run.json')):
            r=read(p)
            if Path(r['source']).name==f'sic-v3-{which}.kicad_sch':runs.append((p,r))
        p,r=runs[-1];record(p);root=EXAMPLE/f'kicad/{folder}'
        stale=[a for a,h in r['dependency_sha256'].items() if sha(root/a)!=h]
        check(which+'_native_erc',r['status']=='passed' and not r['finding_count'] and not stale and sha(p.parent/'erc.json')==r['report_sha256'],dict(run=p.relative_to(EXAMPLE).as_posix(),stale=stale))
    powerhash=sha(EXAMPLE/'kicad/power_board/sic-v3-power.kicad_pcb')
    for f in ['power_projected_isolation','power_copper_dc_mesh','power_closed_loops','quiet_star_topology','switch_node_area']:
        p=EXAMPLE/f'verification/engineering_checks/{f}.json';d=read(p);record(p);check(f+'_current_input',d['board_sha256']==powerhash)
        if f=='power_projected_isolation':check(f,d['passed'])
        if f=='power_copper_dc_mesh':check(f,all(x['status']=='mesh_solved' for x in d['cases']) and len(d['cases'])==12)
        if f=='quiet_star_topology':check(f,all(x['removal_test']['load_terminals_remain_connected'] for x in d['stars']))
    p=EXAMPLE/'simulation/results/provenance.json';d=read(p);record(p)
    stale=[]
    for a,h in d['source_sha256'].items():
        local=Path('automation/'+a.replace('\\','/').split('automation/',1)[1])
        if sha(local)!=h:stale.append(a)
    check('simulation_input_hashes',not stale,stale)
    from automation.sic_v3.calculations import calculate
    check('calculation_reproduction',read(EXAMPLE/'calculations/results.json')==json.loads(json.dumps(calculate())))
    p=EXAMPLE/'verification/regression/unittest.log';text=p.read_text(encoding='utf-8-sig');record(p)
    check('regression_executed',bool(re.search(r'Ran 373 tests',text) and 'OK (skipped=2)' in text),dict(tests=373,skipped=2))
    p=EXAMPLE/'verification/regression/knowledge.log';record(p);check('knowledge_schema', 'RESULT: PASS' in p.read_text(), '19 older component cache checks skipped; not a fresh part-number certification')
    p=EXAMPLE/'verification/engineering_checks/visual_review.json';v=read(p);record(p)
    check('visual_review_current',v['reviewed'] and all(sha(EXAMPLE/a)==h for a,h in v['files'].items()))
    historical=['examples/buck-48v-24v-1kw','examples/sic-buck-400v-200v-5kw'];baseline='20e96fdfa5ea76649daa416ee70b7ea7798a319d'
    changed=subprocess.check_output(['git','diff','--name-only',baseline,'--',*historical],text=True).strip()
    check('historical_designs_unchanged',not changed,changed)
    report=dict(status='CAD_AND_REVIEW_EVIDENCE_VERIFIED' if not findings else 'FAILED',hardware_status='HARDWARE VALIDATION PENDING; RELEASE BLOCKED',
                baseline_commit=baseline,checks=checks,failed_checks=findings,input_sha256=inputs,
                scope='Recorded CAD/model/export/document/test evidence only. No hardware release or human engineering approval.')
    (EXAMPLE/'verification/final_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],findings)
    if findings:raise SystemExit(1)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['netlists','evidence']);a=p.parse_args();globals()[a.stage]()
