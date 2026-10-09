"""Create a non-overwritable V1 snapshot and verify every frozen file hash."""
import hashlib
import json
import shutil
import subprocess
from datetime import datetime,timezone
from pathlib import Path
from automation.kicad_tools.buck_model import EXAMPLE
from automation.verification.verify_buck import verify


def main():
    evidence=verify()
    target=EXAMPLE/'releases/v1'
    target.mkdir(parents=True,exist_ok=False)
    for folder in ('input','design','components','kicad','manufacturing','review'):
        shutil.copytree(EXAMPLE/folder,target/folder)
    checks=target/'verification';checks.mkdir()
    for name in ('ERC_report.json','DRC_report.json','verification-summary.json',
                 'power-layout-metrics.json','pcb_rule_review.md','known_issues.md','visual-review.json'):
        shutil.copyfile(EXAMPLE/'verification'/name,checks/name)
    for kind in ('erc','drc'):
        source=EXAMPLE/evidence[kind]['manifest']
        shutil.copytree(source.parent,checks/source.parent.name)
    (target/'README.md').write_text('''# Frozen V1 review prototype

AI-GENERATED ENGINEERING PROTOTYPE - V1 - HUMAN REVIEW REQUIRED

Start with review/design_report.md, review/schematic.pdf and review/pcb_layout.pdf.
Read verification/known_issues.md before any physical work. Sources and exported
manufacturing formats are included, but no fabrication order is authorized.

This snapshot must not be overwritten. Future reviewed changes belong in V2.
SHA256SUMS.json covers every file except itself. Original-host absolute paths
inside native command logs are historical evidence; relative content paths
inside this snapshot remain usable. No private host configuration is included.
''',encoding='utf8')
    manifest=dict(release='v1',created_utc=datetime.now(timezone.utc).isoformat(),
                  source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                  status='frozen CAD review prototype; hardware unqualified',files={})
    for p in sorted(target.rglob('*')):
        if p.is_file():manifest['files'][p.relative_to(target).as_posix()]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    (target/'SHA256SUMS.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    for name,data in manifest['files'].items():assert hashlib.sha256((target/name).read_bytes()).hexdigest()==data['sha256']
    archive=shutil.make_archive(str(target.parent/'v1-review-package'),'zip',root_dir=target)
    print(json.dumps(dict(frozen_files=len(manifest['files']),path=str(target),archive=archive,source_commit=manifest['source_commit'])))


if __name__=='__main__':main()
