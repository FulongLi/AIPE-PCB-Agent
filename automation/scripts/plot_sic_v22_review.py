"""Render current review PDFs and equal-coordinate native before/after copper plots.

Uses existing PyMuPDF/Pillow and KiCad CLI; never saves or refills an input board.
Page PNGs/contact sheets are temporary. Comparison PNGs and source hashes are review artifacts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont

from automation.kicad_tools.sic_buck_common import EXAMPLE


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kicad-cli', default='kicad-cli')
    args = parser.parse_args()
    scratch = Path('.aipe/v22/visual_qa').resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    out = EXAMPLE / 'review/v22'
    font = ImageFont.truetype('arial.ttf', 22)
    evidence = {'method': 'Native KiCad SVG at 1:1 coordinates; B.Cu, B.Fab, Edge.Cuts; no mirroring/refill', 'comparisons': {}, 'pdfs': {}}
    crops = {'power': [('bias', (155, 129, 178, 142), 'R57 sense-bias RLIM')],
             'control': [('reset', (9, 41, 23, 54), 'U4 reset / C76'),
                         ('logic', (48, 53, 78, 77), 'U8, U10, U11 / C77-C79')]}
    for label in ('power', 'control'):
        pair = {}
        for state, root in [('before', EXAMPLE/'releases/v2.1'), ('after', EXAMPLE)]:
            board = root / f'kicad/{label}_board/AIPE_SiC_Buck_{label.title()}.kicad_pcb'
            svg = scratch / f'{label}-{state}.svg'
            subprocess.run([args.kicad_cli, 'pcb', 'export', 'svg', '--mode-single', '--layers', 'B.Cu,B.Fab,Edge.Cuts',
                            '--page-size-mode', '1', '--exclude-drawing-sheet', '--scale', '1', '-o', str(svg), str(board)], check=True)
            with fitz.open(svg) as drawing:
                document = fitz.open('pdf', drawing.convert_to_pdf())
            pair[state] = document
            evidence['comparisons'][f'{label}_{state}'] = {'board': str(board.relative_to(EXAMPLE)), 'sha256': digest(board)}
        for name, bounds, title in crops[label]:
            mm = 72 / 25.4
            clip = fitz.Rect(*(v * mm for v in bounds))
            width = 900
            height = round(width * clip.height / clip.width)
            canvas = Image.new('RGB', (2 * width + 60, height + 100), 'white')
            draw = ImageDraw.Draw(canvas)
            draw.text((20, 10), f'{title} - native copper, same scale, board coordinates in mm', fill='black', font=font)
            for i, state in enumerate(('before', 'after')):
                pix = pair[state][0].get_pixmap(matrix=fitz.Matrix(width / clip.width, width / clip.width), clip=clip, alpha=False)
                panel = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
                canvas.paste(panel, (20 + i*(width+20), 80))
                draw.text((20 + i*(width+20), 45), f'{"V2.1" if state == "before" else "V2.2"}: x={bounds[0]}..{bounds[2]}, y={bounds[1]}..{bounds[3]}', fill='black', font=font)
            target = out / f'comparison_{label}_{name}.png'
            canvas.save(target)
            evidence['comparisons'][target.name] = {'bounds_mm': bounds, 'sha256': digest(target)}
        for document in pair.values():
            document.close()
    for name in ('schematic_power', 'schematic_control', 'pcb_layout_power', 'pcb_layout_control'):
        pdf = EXAMPLE / f'review/{name}.pdf'
        with fitz.open(pdf) as document:
            evidence['pdfs'][name] = {'pages': len(document), 'sha256': digest(pdf)}
            sheets = []
            for index, page in enumerate(document):
                pix = page.get_pixmap(matrix=fitz.Matrix(1800 / page.rect.width, 1800 / page.rect.width), alpha=False)
                picture = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
                picture.save(scratch / f'{name}-{index+1}.png')
                picture.thumbnail((900, 640))
                if index % 4 == 0:
                    sheets.append(Image.new('RGB', (1840, 1360), '#eeeeee'))
                x, y = (index % 2)*920, ((index % 4)//2)*680
                sheets[-1].paste(picture, (x+10,y+35))
                ImageDraw.Draw(sheets[-1]).text((x+10,y+5), f'{name} / {index+1}', fill='black', font=font)
            for index, sheet in enumerate(sheets):
                sheet.save(scratch / f'{name}-contact-{index+1}.png')
    (out/'visual_artifacts.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf-8')
    print(scratch)


if __name__ == '__main__':
    main()
