"""Custom footprints and envelope models of the DAB-V1 boards (generic generators of project_footprints).

Every isolation package gets an AIPE footprint whose inner land edges are 8.0 mm or more apart so that the
reinforced HV-to-SELV rule of the board is met by the package land pattern itself; the body dimensions are the
manufacturer's, the envelope boxes are reserved volumes, not vendor CAD.  Dimensions marked "envelope" in
requirements/components.yaml need independent review against the manufacturer drawing.
"""
from __future__ import annotations

from automation.kicad_tools import project_footprints as pf

BODY = (0.15, 0.15, 0.15)
FILM = (0.2, 0.3, 0.6)


def dual_row_smd(name: str, count: int, pitch: float, span: float, pad_w: float, pad_h: float, body_w: float, body_h: float,
                 height: float, description: str, *, tags: str = '', extra: str = '') -> tuple[str, list]:
    """SOIC-style dual-row footprint: pins 1..n/2 down the left column, n/2+1..n up the right column.

    ``span`` is the pad-centre distance across the package; the courtyard is drawn around the pad ends, not only
    around the body, so courtyard screening sees the lands.
    """
    per_side = count // 2
    y0 = -(per_side - 1) * pitch / 2
    pads = [pf.smd_pad(str(i + 1), -span / 2, y0 + i * pitch, pad_w, pad_h, 'roundrect') for i in range(per_side)]
    pads += [pf.smd_pad(str(per_side + i + 1), span / 2, -y0 - i * pitch, pad_w, pad_h, 'roundrect') for i in range(per_side)]
    ext_x = (span + pad_w) / 2 + 0.25
    ext_y = max(body_h / 2, -y0 + pad_h / 2) + 0.25
    courtyard = (f'(fp_rect (start {pf.num(-ext_x)} {pf.num(-ext_y)}) (end {pf.num(ext_x)} {pf.num(ext_y)}) '
                 '(stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))')
    pin1 = (f'(fp_circle (center {pf.num(-body_w / 2 + 0.6)} {pf.num(-body_h / 2 + 0.6)}) (end {pf.num(-body_w / 2 + 0.9)} {pf.num(-body_h / 2 + 0.6)}) '
            '(stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))')
    text = pf.make_footprint(name, '\n  '.join(pads), body_w, body_h, description, name, courtyard_margin=0.25, silkscreen=False,
                             tags=tags, extra=courtyard + '\n  ' + pin1 + ('\n  ' + extra if extra else ''))
    import re
    # keep one courtyard: drop the body-only contour that make_footprint drew
    text = re.sub(r'\(fp_rect \(start [^\n]+\(layer "F\.CrtYd"\)\)\n  ', '', text, count=1)
    return text, [(0, 0, height / 2 + 0.1, body_w, body_h, height, BODY)]


def land_gap(text: str) -> float:
    """Inner land-edge gap (mm) between the two pad columns of a dual-row footprint text (barrier check)."""
    pads = pf.pads_in_text(text)
    left = max(p['at'][0] + p['size'][0] / 2 for p in pads if p['number'] and p['at'][0] < 0)
    right = min(p['at'][0] - p['size'][0] / 2 for p in pads if p['number'] and p['at'][0] > 0)
    return round(right - left, 3)


def tmcs1133_footprint(name='DAB_TMCS1133_DVG') -> tuple[str, list]:
    """TI DVG0010A Hall sensor, HV land option: two current bars (pads 1 IN+, 2 IN-) 3.0 x 4.41 mm on a 5.08 mm pitch,
    inner edge at x = -4.0; eight SELV pads 2.0 x 0.6 mm at 1.27 mm with inner edge at x = +4.0 (8.0 mm land gap);
    body 7.5 x 10.3 x 2.65 mm (SBOSAG0E DVG0010A, bars widened outward as in the V2 footprint)."""
    bars = [pf.smd_pad('1', -5.5, -2.54, 3.0, 4.41), pf.smd_pad('2', -5.5, 2.54, 3.0, 4.41)]
    selv = [pf.smd_pad(str(3 + i), 5.0, 4.445 - i * 1.27, 2.0, 0.6, 'roundrect') for i in range(8)]
    courtyard = '(fp_rect (start -7.3 -5.4) (end 6.3 5.4) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))'
    pin1 = '(fp_circle (center -3.0 -4.5) (end -2.7 -4.5) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))'
    text = pf.make_footprint(name, '\n  '.join(bars + selv), 7.5, 10.3,
                             'TMCS1133 DVG0010A (10-pin wide SOIC, two current leads) - TI HV land option with the bars widened '
                             'outward to 3.0 x 4.41 mm; inner land edges at +/-4.0 mm (8.0 mm gap); body 7.5 x 10.3 x 2.65 mm; '
                             'AIPE footprint from SBOSAG0E, review against the drawing', name, courtyard_margin=0.25, silkscreen=False,
                             tags='TMCS1133 DVG Hall sensor isolated', extra=courtyard + '\n  ' + pin1)
    import re
    text = re.sub(r'\(fp_rect \(start [^\n]+\(layer "F\.CrtYd"\)\)\n  ', '', text, count=1)
    return text, [(0, 0, 1.425, 7.5, 10.3, 2.65, BODY)]


def custom(components: dict) -> dict:
    """name -> (kicad_mod text, envelope boxes) for every AIPE footprint the DAB models reference."""
    out = {}
    out['DAB_UCC21710_DW_HV'] = dual_row_smd(
        'DAB_UCC21710_DW_HV', 16, 1.27, 9.75, 1.65, 0.6, 7.5, 10.3, 2.65,
        'UCC21710 SOIC-16 DW wide body: TI land pattern 16 x 1.65 x 0.6 mm at 1.27 mm, centre span 9.75 mm (inner land gap '
        '8.1 mm); body 7.5 x 10.3 x 2.65 mm; AIPE footprint from SLUSDH8D, review against the drawing',
        tags='UCC21710 DW isolated gate driver')
    out['DAB_UCC14141_DWN'] = dual_row_smd(
        'DAB_UCC14141_DWN', 36, 0.65, 9.95, 1.85, 0.40, 7.5, 12.83, 3.55,
        'UCC14141-Q1 DWN0036A 36-pin SSOP: narrow-land variant of the TI pattern (0.40 mm instead of 0.45 mm pad width at 0.65 mm '
        'pitch, 0.39 mm maximum lead) keeping the 0.25 mm board clearance; centre span 9.95 mm (inner land gap 8.1 mm); body '
        '7.5 x 12.83 x 3.55 mm; assembly qualification of the narrow land is required (SLUSF10B)',
        tags='UCC14141 DWN isolated DC-DC')
    for name, part in (('DAB_AMC1311_DWV', 'AMC1311'), ('DAB_AMC1336_DWV', 'AMC1336')):
        out[name] = dual_row_smd(
            name, 8, 1.27, 10.9, 1.8, 0.6, 7.5, 5.85, 2.8,
            f'{part} DWV0008A wide-body SOIC-8: TI land pattern 8 x 1.8 x 0.6 mm at 1.27 mm, centre span 10.9 mm (inner land gap '
            '9.1 mm); body 7.5 x 5.85 x 2.8 mm; AIPE footprint, review against the drawing', tags=f'{part} DWV isolated')
    out['DAB_TMCS1133_DVG'] = tmcs1133_footprint()
    out['DAB_DGK8'] = dual_row_smd('DAB_DGK8', 8, 0.65, 4.4, 1.4, 0.45, 3.0, 3.0, 1.1,
                                   'TI DGK0008A (VSSOP-8) land pattern 4214862/A with 0.45 mm wide lands at 0.65 mm pitch (0.20 mm land gap); '
                                   'non-isolated; body 3.0 x 3.0 x 1.1 mm', tags='VSSOP-8 DGK')
    hs = components['heatsink']['envelope_mm']
    out['DAB_HEATSINK_ENVELOPE'] = pf.heatsink_envelope_footprint(
        'DAB_HEATSINK_ENVELOPE', hs[0], hs[1], hs[2], mounting_holes=[(-20.0, 0.0, 3.4), (20.0, 0.0, 3.4)],
        keepout=('tracks', 'vias', 'footprints', 'copperpour'), keepout_layers=('F.Cu',))
    for side in ('primary', 'secondary'):
        film = components['dc_link'][side]['film']
        L, W, H = film['envelope_mm']
        out[f'DAB_FILM_{side.upper()}'] = pf.film_capacitor_footprint(
            f'DAB_FILM_{side.upper()}', film['pitch_mm'][0], L, W, H, film['drill_mm'], pins=4, second_pitch_mm=film['pitch_mm'][1], pad_mm=2.8)
    blk = components['dc_block']
    L, W, H = blk['envelope_mm']
    out['DAB_CBLK_FILM'] = pf.film_capacitor_footprint('DAB_CBLK_FILM', blk['pitch_mm'], L, W, H, blk['drill_mm'], pins=2, pad_mm=2.0)
    return out


def barrier_footprints() -> tuple[str, ...]:
    return ('DAB_UCC21710_DW_HV', 'DAB_UCC14141_DWN', 'DAB_AMC1311_DWV', 'DAB_AMC1336_DWV', 'DAB_TMCS1133_DVG')
