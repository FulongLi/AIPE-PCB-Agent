"""Assemble V3 review copies, render native PDFs, and hash the final package.

Rendering is a QA aid; visual review is still required. Never calls a router.
"""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path
from automation.sic_v3.model import EXAMPLE


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def render():
    from automation.setup.detect_kicad import find_kicad_cli
    for which in ['power','control']:
        root=EXAMPLE/f'manufacturing/{which}'
        output=root/'review/pcb_3d.png';log=root/'logs/isometric.log'
        command=[str(find_kicad_cli()),'pcb','render','--side','top','--rotate','330,0,25','--zoom','.88','--width','1600','--height','1200','-o',str(output),str(EXAMPLE/f'kicad/{which}_board/sic-v3-{which}.kicad_pcb')]
        run=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',check=True)
        log.write_text(run.stdout+run.stderr,encoding='utf-8')
        path=root/'export-manifest.json';manifest=json.loads(path.read_text())
        row=next(r for r in manifest['commands'] if r['name']=='isometric');row.update(command=command,exit_code=0,revision_reason='Visual QA: leave margin for tall capacitor bodies')
        for p in [output,log]:manifest['artifacts'][p.relative_to(root).as_posix()]=dict(bytes=p.stat().st_size,sha256=sha(p))
        path.write_text(json.dumps(manifest,indent=2)+'\n')


def prepare():
    import fitz
    from PIL import Image,ImageDraw
    review=EXAMPLE/'review';qa=Path('.aipe/v3/pdf-qa');qa.mkdir(parents=True,exist_ok=True)
    for which in ['power','control']:
        src=EXAMPLE/f'manufacturing/{which}/review'
        for a,b in [('schematic.pdf',f'schematic_{which}.pdf'),('pcb_layout.pdf',f'pcb_{which}.pdf'),('pcb_3d.png',f'pcb_{which}_3d.png')]:shutil.copyfile(src/a,review/b)
        native=EXAMPLE/f'verification/drc/{which}.json';report=json.loads(native.read_text())
        path=EXAMPLE/f'pcb/routing_analysis/{which}_native_completion.json';m=json.loads(path.read_text())
        m.update(board_sha256=sha(EXAMPLE/m['board']),report_sha256=sha(native),ignored_checks=report.get('ignored_checks',[]))
        assert not any(report[k] for k in ['violations','unconnected_items','schematic_parity'])
        path.write_text(json.dumps(m,indent=2)+'\n')
    checks=[]
    for p in sorted(review.glob('*.pdf')):
        doc=fitz.open(p);pages=[]
        for i,page in enumerate(doc):
            pix=page.get_pixmap(matrix=fitz.Matrix(1.6,1.6));png=qa/f'{p.stem}-{i+1:02}.png';pix.save(png)
            outside=[]
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines',[]):
                    for span in line['spans']:
                        if not page.rect.contains(fitz.Rect(span['bbox'])):outside.append(span['text'])
            pages.append(dict(page=i+1,width_pt=page.rect.width,height_pt=page.rect.height,text_outside_page=outside))
        for start in range(0,len(doc),4):
            sheet=Image.new('RGB',(1800,1320),'#dddddd');draw=ImageDraw.Draw(sheet)
            for j in range(start,min(start+4,len(doc))):
                im=Image.open(qa/f'{p.stem}-{j+1:02}.png');im.thumbnail((890,625));x=(j-start)%2*900;y=(j-start)//2*660
                sheet.paste(im,(x,y+25));draw.text((x+8,y+6),f'{p.stem}: page {j+1}',fill='black')
            sheet.save(qa/f'{p.stem}-sheet-{start//4+1}.png')
        if p.stem in ['pcb_power','pcb_control']:
            doc[0].get_pixmap(matrix=fitz.Matrix(2,2)).save(review/f'{p.stem}.png')
        checks.append(dict(file=p.relative_to(EXAMPLE).as_posix(),sha256=sha(p),pages=pages))
    (EXAMPLE/'verification/engineering_checks/pdf_bounds.json').write_text(json.dumps(dict(scope='Text bounding boxes and raster outputs only; visual review recorded separately',files=checks),indent=2)+'\n')
    print([(x['file'],len(x['pages']),sum(len(y['text_outside_page']) for y in x['pages'])) for x in checks])


def freeze():
    path=EXAMPLE/'review/package_manifest.json'
    files={p.relative_to(EXAMPLE).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(EXAMPLE.rglob('*')) if p.is_file() and p!=path and not p.name.endswith(('.lck','.kicad_prl'))}
    path.write_text(json.dumps(dict(baseline_commit='20e96fdfa5ea76649daa416ee70b7ea7798a319d',
        status='ENGINEERING PROTOTYPE REVIEW; RELEASE BLOCKED; NO HARDWARE QUALIFICATION',
        manifest_excludes='This manifest itself; lock/local GUI preference files',files=files),indent=2)+'\n')
    print('Frozen files',len(files))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['render','prepare','freeze']);a=p.parse_args();globals()[a.stage]()
