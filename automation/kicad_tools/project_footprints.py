"""Project footprint libraries for any AIPE electrical model; not tied to V1.

Generalises automation/kicad_tools/buck_footprints.py (frozen with V1): the
official footprints used by a part list are copied into
<kicad_dir>/libraries/<Lib>.pretty, custom footprints and their dimensioned
envelope models go to AIPE.pretty / AIPE.3dshapes, fp-lib-table and the KiCad
library licence notices are written, and the part list's pad/net mapping is
checked against the real pad numbers before any schematic exists.

Deterministic (standard library only): library discovery, s-expression pad
parsing, pad/net validation, footprint text generation (fixed format version,
uuid5 ids, no timestamps), model rewriting and every file written here, so a
second run reproduces identical bytes. Still requires native KiCad: only
pcbnew.FootprintLoad and kicad-cli DRC decide whether a generated footprint is
valid; this module checks balanced syntax and pad arithmetic, not CAD
semantics. Package dimensions are caller inputs that need independent review
against the manufacturer drawings; a passing DRC does not prove package fit.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
from pathlib import Path

from automation.kicad_tools.buck_footprints import data_root  # re-exported; V1 code is not modified
from automation.kicad_tools.native_schematic import children, parse, uid
from automation.kicad_tools.simple_models import write_model

ROOT = Path(__file__).resolve().parents[2]
SMOKE_LIBRARIES = ROOT / 'examples/automation-smoke/kicad/libraries'
CUSTOM_LIB = 'AIPE'
FOOTPRINT_VERSION = 20260206  # written by the KiCad 10.0.7 library files and by the V1 generator
PAD_SHAPES = ('circle', 'oval', 'rect', 'roundrect')
KEEPOUT_ITEMS = ('tracks', 'vias', 'pads', 'copperpour', 'footprints')
NAME_PATTERN = re.compile(r'[A-Za-z0-9_.,+\-]+')
METAL = (0.72, 0.72, 0.75)


def num(value) -> str:
    """Format a millimetre value compactly and deterministically (at most four decimals)."""
    text = f'{float(value):.4f}'.rstrip('0').rstrip('.')
    return '0' if text in ('', '-0') else text


# --- discovery and pad parsing -------------------------------------------------

def footprints_root(source=None):
    """Directory holding <Lib>.pretty folders: `source`, else $AIPE_KICAD_DATA/footprints, else the
    detected KiCad data root (buck_footprints.data_root); None when no KiCad is configured."""
    if source is not None:
        return Path(source)
    env = os.environ.get('AIPE_KICAD_DATA')
    if env:
        return Path(env) / 'footprints'
    try:
        return data_root() / 'footprints'
    except (AttributeError, FileNotFoundError):
        return None


def installed_footprint(lib, name, source=None):
    """Path of an installed <lib>.pretty/<name>.kicad_mod, or None."""
    root = footprints_root(source)
    if root is None:
        return None
    path = root / f'{lib}.pretty' / f'{name}.kicad_mod'
    return path if path.is_file() else None


def footprint_available(lib, name, source=None) -> bool:
    """True when the official footprint exists in the installed (or given) library root."""
    return installed_footprint(lib, name, source) is not None


def pads_in_text(text) -> list[dict]:
    """Pad records (number, type, shape, at, size, drill, layers) parsed from .kicad_mod text."""
    tree = parse(text)
    if tree[0] != 'footprint':
        raise ValueError('Not a footprint s-expression')
    records = []
    for pad in children(tree, 'pad'):
        at, size, drill, layers = (children(pad, key) for key in ('at', 'size', 'drill', 'layers'))
        record = dict(number=str(pad[1]), type=pad[2], shape=pad[3],
                      at=[float(v) for v in at[0][1:3]] if at else [0.0, 0.0],
                      size=[float(v) for v in size[0][1:3]] if size else [0.0, 0.0],
                      drill=None, layers=list(layers[0][1:]) if layers else [])
        if drill:
            values = [float(v) for v in drill[0][1:] if not isinstance(v, list) and v != 'oval']
            record['drill'] = values[0] if len(values) == 1 else (values or None)
        records.append(record)
    return records


def pad_numbers(pads) -> list[str]:
    """Unique non-empty pad numbers in file order; unnumbered holes are mechanical, not electrical."""
    numbers = []
    for pad in pads:
        if pad['number'] and pad['number'] not in numbers:
            numbers.append(pad['number'])
    return numbers


def footprint_pad_details(lib, name, source=None) -> list[dict]:
    """Pad records of an installed official footprint (FileNotFoundError when absent)."""
    path = installed_footprint(lib, name, source)
    if path is None:
        raise FileNotFoundError(f'Footprint {lib}:{name} is not installed')
    return pads_in_text(path.read_text(encoding='utf-8-sig'))


def footprint_pads(lib, name, source=None) -> list[str]:
    """Electrical pad numbers of an installed footprint, for checking a part's nets before CAD."""
    return pad_numbers(footprint_pad_details(lib, name, source))


def split_footprint(part) -> tuple[str, str]:
    """(lib, name) of a part's "Lib:Name" footprint id."""
    footprint = part.get('footprint', '')
    if footprint.count(':') != 1:
        raise ValueError(f"{part.get('ref')}: footprint must be 'Lib:Name', got {footprint!r}")
    lib, name = footprint.split(':')
    return lib, name


def select_parts(parts, board=None) -> list[dict]:
    """Parts of one board ("power" | "control" via the optional part key); all parts when board is None."""
    return [p for p in parts if p.get('on_board', True) and (board is None or p.get('board') == board)]


def custom_text(value) -> str:
    """Footprint text from a custom_footprints value: plain text or a (text, boxes) generator result."""
    return value[0] if isinstance(value, (tuple, list)) else value


def validate_pad_mapping(parts, custom_footprints=None, source=None, board=None) -> list[str]:
    """Mismatches between each part's nets keys and its footprint's pad numbers; an empty list means consistent."""
    custom = custom_footprints or {}
    cache, issues = {}, []
    for part in select_parts(parts, board):
        lib, name = split_footprint(part)
        if (lib, name) not in cache:
            if lib == CUSTOM_LIB and name in custom:
                pads = pad_numbers(pads_in_text(custom_text(custom[name])))
            else:  # official library, or an AIPE footprint already written under `source`
                path = installed_footprint(lib, name, source)
                pads = pad_numbers(pads_in_text(path.read_text(encoding='utf-8-sig'))) if path else None
            cache[lib, name] = pads
        pads = cache[lib, name]
        if pads is None:
            issues.append(f"{part['ref']}: footprint {lib}:{name} not found")
            continue
        nets = {str(k) for k in part.get('nets', {})}
        missing, extra = sorted(set(pads) - nets), sorted(nets - set(pads))
        if missing or extra:
            issues.append(f"{part['ref']} {lib}:{name}: pads without net {missing}, nets without pad {extra}")
    return issues


# --- footprint text generation --------------------------------------------------

def _pair(value):
    return (float(value), float(value)) if isinstance(value, (int, float)) else (float(value[0]), float(value[1]))


def tht_pad(number, x, y, size, drill, shape='circle') -> str:
    """Plated through-hole pad; `size` and `drill` are a diameter or (w, h), a (w, h) drill being a slot."""
    if shape not in PAD_SHAPES:
        raise ValueError(f'Unsupported pad shape {shape!r}')
    w, h = _pair(size)
    dw, dh = _pair(drill)
    if w <= dw or h <= dh:
        raise ValueError(f'Pad {number}: size {size} leaves no annular ring around drill {drill}')
    hole = f'(drill {num(dw)})' if isinstance(drill, (int, float)) else f'(drill oval {num(dw)} {num(dh)})'
    corner = ' (roundrect_rratio 0.25)' if shape == 'roundrect' else ''
    return (f'(pad "{number}" thru_hole {shape} (at {num(x)} {num(y)}) (size {num(w)} {num(h)}) {hole} '
            f'(layers "*.Cu" "*.Mask") (remove_unused_layers no){corner})')


def npth_pad(x, y, drill) -> str:
    """Unplated mechanical hole without copper, as KiCad's MountingHole footprints use."""
    return (f'(pad "" np_thru_hole circle (at {num(x)} {num(y)}) (size {num(drill)} {num(drill)}) '
            f'(drill {num(drill)}) (layers "*.Cu" "*.Mask"))')


def smd_pad(number, x, y, w, h, shape='rect') -> str:
    """Top-side SMD pad with paste and mask openings."""
    if shape not in PAD_SHAPES:
        raise ValueError(f'Unsupported pad shape {shape!r}')
    corner = ' (roundrect_rratio 0.25)' if shape == 'roundrect' else ''
    return (f'(pad "{number}" smd {shape} (at {num(x)} {num(y)}) (size {num(w)} {num(h)}) '
            f'(layers "F.Cu" "F.Paste" "F.Mask"){corner})')


def keepout_zone(name, points, layers=('F.Cu',), forbid=('tracks', 'vias', 'footprints')) -> str:
    """Footprint-embedded rule area over `points`; `forbid` lists the KEEPOUT_ITEMS not allowed inside it."""
    unknown = set(forbid) - set(KEEPOUT_ITEMS)
    if unknown:
        raise ValueError(f'Unknown keepout items {sorted(unknown)}')
    layer = f'(layer "{layers[0]}")' if len(layers) == 1 else '(layers ' + ' '.join(f'"{l}"' for l in layers) + ')'
    rules = ' '.join(f'({item} {"not_allowed" if item in forbid else "allowed"})' for item in KEEPOUT_ITEMS)
    pts = ' '.join(f'(xy {num(x)} {num(y)})' for x, y in points)
    return (f'(zone {layer} (uuid "{uid("footprint/" + name + "/keepout")}") (name "{name}_keepout") (hatch full 0.508) '
            f'(connect_pads (clearance 0)) (min_thickness 0.254) (keepout {rules}) (placement (enabled no) (sheetname "")) '
            f'(fill (thermal_gap 0.508) (thermal_bridge_width 0.508) (island_removal_mode 0)) (polygon (pts {pts})))')


def footprint_attr(pads_sexpr) -> str:
    """KiCad footprint type inferred from the pads: through_hole, smd, or mechanical (NPTH only)."""
    if re.search(r'\(pad "[^"]*" thru_hole', pads_sexpr):
        return 'through_hole'
    if re.search(r'\(pad "[^"]*" smd', pads_sexpr):
        return 'smd'
    return 'through_hole exclude_from_pos_files' if 'np_thru_hole' in pads_sexpr else ''


def make_footprint(name, pads_sexpr, width, height, description, model_name=None, *, attr=None, shape='rect',
                   courtyard_margin=0.5, silkscreen=True, tags='', extra='') -> str:
    """Footprint text: F.Fab body (rect width x height, or a circle of diameter `width`), F.CrtYd grown by
    `courtyard_margin`, optional F.SilkS outline, the pads, `extra` items (e.g. a keepout_zone) and a reference to the
    AIPE envelope model `model_name` when given. `attr` None infers the footprint type from the pads."""
    if not NAME_PATTERN.fullmatch(name):
        raise ValueError(f'Footprint name {name!r} must use letters, digits, _ . , + -')
    if shape not in ('rect', 'circle'):
        raise ValueError(f'Unsupported body shape {shape!r}')
    if width <= 0 or height <= 0:
        raise ValueError('Body dimensions must be positive')
    w, h = (width, width) if shape == 'circle' else (width, height)
    attr = footprint_attr(pads_sexpr) if attr is None else attr

    def outline(grow, layer, stroke):
        """Body outline grown by `grow` mm on `layer`."""
        if shape == 'circle':
            return (f'(fp_circle (center 0 0) (end {num(w / 2 + grow)} 0) (stroke (width {stroke}) (type default)) '
                    f'(fill none) (layer "{layer}"))')
        return (f'(fp_rect (start {num(-w / 2 - grow)} {num(-h / 2 - grow)}) (end {num(w / 2 + grow)} {num(h / 2 + grow)}) '
                f'(stroke (width {stroke}) (type default)) (fill none) (layer "{layer}"))')

    items = [outline(0, 'F.Fab', 0.1), outline(courtyard_margin, 'F.CrtYd', 0.05)]
    if silkscreen:
        items.append(outline(0.11, 'F.SilkS', 0.12))
    graphics = '\n  '.join(items)
    model = (f'\n  (model "${{KIPRJMOD}}/libraries/{CUSTOM_LIB}.3dshapes/{model_name}.wrl" '
             '(offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))' if model_name else '')
    text = f'''(footprint "{name}" (version {FOOTPRINT_VERSION}) (generator "aipe") (layer "F.Cu")
  (descr {json.dumps(description)}){f' (tags {json.dumps(tags)})' if tags else ''}
  (property "Reference" "REF**" (at 0 {num(-h / 2 - 2)} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (property "Value" "{name}" (at 0 {num(h / 2 + 2)} 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
  {f'(attr {attr})' if attr else ''}
  {graphics}
  (fp_text user "${{REFERENCE}}" (at 0 0 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
  {pads_sexpr}
  {extra}{model}
)
'''
    parse(text)
    return text


def toroid_inductor_footprint(name, pitch_mm, hole_mm, pad_mm, body_diameter_mm, body_height_mm, mount_hole_mm=None,
                              *, upright=False):
    """Powder-core toroid with two heavy leads. Default: core lying flat (axis vertical) so the optional central
    NPTH `mount_hole_mm` takes a bolt with an insulating washer; `upright=True` stands the core on its rim (outline =
    diameter x core height, bracket mounting). Returns (kicad_mod_text, envelope boxes for write_model)."""
    for label, value in (('pitch', pitch_mm), ('hole', hole_mm), ('pad', pad_mm),
                         ('body diameter', body_diameter_mm), ('body height', body_height_mm)):
        if value <= 0:
            raise ValueError(f'{label} must be positive')
    if mount_hole_mm and mount_hole_mm + pad_mm >= pitch_mm:
        raise ValueError('Central mounting hole would reach the lead pads')
    pads = [tht_pad('1', -pitch_mm / 2, 0, pad_mm, hole_mm), tht_pad('2', pitch_mm / 2, 0, pad_mm, hole_mm)]
    if mount_hole_mm:
        pads.append(npth_pad(0, 0, mount_hole_mm))
    d, hgt = body_diameter_mm, body_height_mm
    mount = (f'; central NPTH {num(mount_hole_mm)} mm for a bolt with insulating washer' if mount_hole_mm
             else '; clamp or potting required')
    common = f'lead pitch {num(pitch_mm)} mm, drill {num(hole_mm)} mm, pad {num(pad_mm)} mm'
    leads_fit = (pitch_mm + pad_mm) / 2 < d / 2 - 0.2
    if upright:
        text = make_footprint(name, '\n  '.join(pads), d, hgt,
                              f'Powder-core toroid standing on its rim, OD {num(d)} mm, core height {num(hgt)} mm, '
                              f'{common}; height above board {num(d)} mm{mount}; AIPE envelope, review against the winding drawing',
                              name, tags='inductor toroid upright', silkscreen=leads_fit and pad_mm / 2 < hgt / 2 - 0.2)
        boxes = [(0, 0, d / 2, d, hgt, d, (0.25, 0.27, 0.3))]
    else:
        text = make_footprint(name, '\n  '.join(pads), d, d,
                              f'Powder-core toroid lying flat (axis vertical), OD {num(d)} mm, height {num(hgt)} mm, '
                              f'{common}{mount}; AIPE envelope, review against the winding drawing',
                              name, shape='circle', tags='inductor toroid flat', silkscreen=leads_fit)
        boxes = [(0, 0, hgt / 2, d, d, hgt, (0.25, 0.27, 0.3))]
    return text, boxes


def heatsink_envelope_footprint(name, width_mm, depth_mm, height_mm, mounting_holes=(), *,
                                keepout=('tracks', 'vias', 'footprints'), keepout_layers=('F.Cu',),
                                plated_number=None, pad_mm=None):
    """Heatsink base envelope width x depth mm (height recorded for the 3D box) with NPTH mounting holes
    [(x, y, drill)] - or plated pads sharing `plated_number` for an electrically bonded heatsink - and an embedded rule
    area forbidding the `keepout` items under the base on `keepout_layers` (None/() for none). No other copper.
    Returns (kicad_mod_text, envelope boxes)."""
    if min(width_mm, depth_mm, height_mm) <= 0:
        raise ValueError('Envelope dimensions must be positive')
    pads = []
    for x, y, drill in mounting_holes:
        if abs(x) + drill / 2 > width_mm / 2 or abs(y) + drill / 2 > depth_mm / 2:
            raise ValueError(f'Mounting hole at ({x}, {y}) lies outside the {width_mm} x {depth_mm} mm base')
        pads.append(tht_pad(plated_number, x, y, pad_mm or round(drill * 1.6, 2), drill) if plated_number
                    else npth_pad(x, y, drill))
    w, d = width_mm / 2, depth_mm / 2
    extra = [f'(fp_text user "HEATSINK H={num(height_mm)}mm" (at 0 {num(min(3, d / 2))} 0) (layer "Cmts.User") '
             '(effects (font (size 1 1) (thickness 0.15))))']
    if keepout:
        extra.append(keepout_zone(name, [(-w, -d), (w, -d), (w, d), (-w, d)], keepout_layers, tuple(keepout)))
    holes = ', '.join(f'({num(x)}, {num(y)}) drill {num(dr)}' for x, y, dr in mounting_holes) or 'none'
    text = make_footprint(name, '\n  '.join(pads), width_mm, depth_mm,
                          f'Heatsink envelope {num(width_mm)} x {num(depth_mm)} mm base, {num(height_mm)} mm tall; '
                          f'mounting holes {holes}; rule area forbids {", ".join(keepout) if keepout else "nothing"} on '
                          f'{"/".join(keepout_layers)}; thermal interface and electrical isolation are separate review items',
                          name, tags='heatsink envelope', extra='\n  '.join(extra), attr='through_hole exclude_from_pos_files')
    return text, [(0, 0, height_mm / 2, width_mm, depth_mm, height_mm, (0.55, 0.57, 0.6))]


def film_capacitor_footprint(name, pitch_mm, length_mm, width_mm, height_mm, lead_drill_mm, pins=2, second_pitch_mm=None,
                             *, pad_mm=None, pad_numbers=None):
    """Box film capacitor length x width x height mm with radial leads on `pitch_mm`; pins=4 adds a second lead per
    electrode `second_pitch_mm` apart across the width (numbered 1,1,2,2 unless `pad_numbers` gives four). The pad
    diameter defaults to twice the drill (KiCad library convention). Returns (kicad_mod_text, envelope boxes)."""
    if pins not in (2, 4):
        raise ValueError('pins must be 2 or 4')
    if pins == 4 and not second_pitch_mm:
        raise ValueError('second_pitch_mm is required for 4 pins')
    pad = pad_mm or round(lead_drill_mm * 2, 2)
    if pitch_mm + pad >= length_mm:
        raise ValueError('Lead pitch plus pad does not fit inside the body length')
    if pins == 4 and second_pitch_mm + pad >= width_mm:
        raise ValueError('Second pitch plus pad does not fit inside the body width')
    x = pitch_mm / 2
    if pins == 2:
        positions, numbers = [(-x, 0), (x, 0)], tuple(pad_numbers or ('1', '2'))
    else:
        y = second_pitch_mm / 2
        positions, numbers = [(-x, -y), (-x, y), (x, -y), (x, y)], tuple(pad_numbers or ('1', '1', '2', '2'))
    if len(numbers) != len(positions):
        raise ValueError('pad_numbers must match the pin count')
    pads = '\n  '.join(tht_pad(n, px, py, pad, lead_drill_mm) for n, (px, py) in zip(numbers, positions))
    second = f' x {num(second_pitch_mm)} mm' if pins == 4 else ''
    text = make_footprint(name, pads, length_mm, width_mm,
                          f'Film capacitor box {num(length_mm)} x {num(width_mm)} x {num(height_mm)} mm, {pins} leads, '
                          f'pitch {num(pitch_mm)} mm{second}, drill {num(lead_drill_mm)} mm, pad {num(pad)} mm; '
                          'AIPE envelope, verify against the manufacturer drawing', name, tags='capacitor film DC-link')
    return text, [(0, 0, height_mm / 2, length_mm, width_mm, height_mm, (0.2, 0.3, 0.6))]


# --- project library preparation ------------------------------------------------

def replace_model(text, model_name) -> str:
    """Point every (model ...) reference of a footprint at an AIPE envelope; append one when the file has none."""
    reference = f'(model "${{KIPRJMOD}}/libraries/{CUSTOM_LIB}.3dshapes/{model_name}.wrl"'
    if re.search(r'\(model "[^"]+"', text):
        return re.sub(r'\(model "[^"]+"', lambda match: reference, text)
    end = text.rstrip().rfind(')')
    return text[:end] + f'\t{reference}\n\t\t(offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))\n' + text[end:]


def notice_markdown(copied, overrides, custom, models, notice_text=None) -> str:
    """Provenance notice for the generated library folder."""
    lines = ['# Library provenance', '', notice_text or (
        'Generated by automation.kicad_tools.project_footprints. Stock copper and pad geometry comes from the official '
        'KiCad footprint library shipped with the configured KiCad installation and keeps its licence (see LICENSE.md '
        'and CC-BY-SA-4.0.txt). Custom AIPE footprints and envelope models were generated from dimensions supplied by '
        'the design model; they need independent dimensional review, and a passing DRC does not establish vendor '
        'package compatibility.'), '']
    sections = (('Official footprints copied unchanged', [c for c in copied if c not in overrides]),
                ('Official footprints with only the 3D model reference replaced by an AIPE envelope',
                 [f'{k} -> {v}' for k, v in sorted(overrides.items())]),
                ('Custom AIPE footprints', [f'{CUSTOM_LIB}:{n}' for n in custom]),
                ('AIPE envelope models (AIPE.3dshapes, STEP and VRML boxes, not vendor CAD)', list(models)))
    for title, items in sections:
        if items:
            lines += [f'## {title}', ''] + [f'- {item}' for item in items] + ['']
    return '\n'.join(lines)


def prepare_libraries(parts, kicad_dir, custom_footprints=None, model_overrides=None, notice_text=None, *,
                      models=None, source=None, board=None, strict=True, descr='AIPE project library') -> dict:
    """Build <kicad_dir>/libraries and fp-lib-table for `parts` (optionally only those with part['board'] == board).

    Official footprints are copied from `source` (default: the installed KiCad library); `custom_footprints` maps name
    to .kicad_mod text or to a (text, boxes) generator result written into AIPE.pretty; `models` maps model name to
    envelope boxes written with simple_models.write_model into AIPE.3dshapes; `model_overrides` maps a ref (or a
    "Lib:Name" id) to a model name whose reference replaces the copied footprint's model, as V1 did. The KiCad library
    licence files and NOTICE.md are written. With `strict`, pad/net mismatches raise ValueError before anything is
    written; otherwise they are returned under 'issues'. Returns a summary dict."""
    kicad_dir = Path(kicad_dir)
    target = kicad_dir / 'libraries'
    custom = {name: custom_text(value) for name, value in (custom_footprints or {}).items()}
    boxes = dict(models or {})
    for name, value in (custom_footprints or {}).items():
        if isinstance(value, (tuple, list)) and value[1]:
            boxes.setdefault(name, value[1])
    selected = select_parts(parts, board)
    issues = validate_pad_mapping(selected, custom, source)
    if strict and issues:
        raise ValueError('Pad/net mapping is inconsistent:\n' + '\n'.join(issues))
    root = footprints_root(source)
    overrides = {}
    for key, model in (model_overrides or {}).items():
        ids = [key] if ':' in key else [p['footprint'] for p in selected if p['ref'] == key]
        if not ids:
            raise KeyError(f'Model override for unknown part {key!r}')
        for footprint in ids:
            if overrides.get(footprint, model) != model:
                raise ValueError(f'Conflicting model overrides for shared footprint {footprint}')
            overrides[footprint] = model
    target.mkdir(parents=True, exist_ok=True)
    libs, copied, warnings = set(), [], []
    for part in selected:
        lib, name = split_footprint(part)
        libs.add(lib)
        destination = target / f'{lib}.pretty'
        destination.mkdir(exist_ok=True)
        if lib == CUSTOM_LIB:
            if name not in custom:
                raise KeyError(f"{part['ref']}: custom footprint {name!r} was not provided")
            continue
        if root is None:
            raise FileNotFoundError('KiCad footprint library not found; configure kicad-cli or set AIPE_KICAD_DATA')
        original = root / f'{lib}.pretty' / f'{name}.kicad_mod'
        if not original.exists():
            raise FileNotFoundError(original)
        file = destination / original.name
        if file.exists():
            file.chmod(stat.S_IREAD | stat.S_IWRITE)
        shutil.copyfile(original, file)
        copied.append(part['footprint'])
    for footprint, model in sorted(overrides.items()):
        if footprint not in copied:
            raise KeyError(f'Model override target {footprint} is not an official footprint of the selected parts')
        lib, name = footprint.split(':', 1)
        file = target / f'{lib}.pretty' / f'{name}.kicad_mod'
        file.write_text(replace_model(file.read_text(encoding='utf-8-sig'), model), encoding='utf-8')
        if model not in boxes:
            warnings.append(f'model override {footprint} -> {model} has no envelope boxes; the model file is missing')
    if custom:
        folder = target / f'{CUSTOM_LIB}.pretty'
        folder.mkdir(exist_ok=True)
        for name, text in sorted(custom.items()):
            parse(text)
            (folder / f'{name}.kicad_mod').write_text(text, encoding='utf-8')
            for referenced in re.findall(rf'{CUSTOM_LIB}\.3dshapes/([^"/]+)\.(?:wrl|step|stp)"', text):
                if referenced not in boxes:
                    warnings.append(f'custom footprint {name} references envelope model {referenced} that is not written')
        libs.add(CUSTOM_LIB)
    for name, model_boxes in sorted(boxes.items()):
        write_model(target / f'{CUSTOM_LIB}.3dshapes', name, model_boxes)
    table = ['(fp_lib_table (version 7)'] + [
        f'(lib (name "{lib}") (type "KiCad") (uri "${{KIPRJMOD}}/libraries/{lib}.pretty") (options "") (descr "{descr}"))'
        for lib in sorted(libs)]
    (kicad_dir / 'fp-lib-table').write_text('\n'.join(table) + ')\n', encoding='utf-8')
    for name in ('LICENSE.md', 'CC-BY-SA-4.0.txt'):
        original = SMOKE_LIBRARIES / name
        if original.exists():
            shutil.copyfile(original, target / name)
        else:
            warnings.append(f'KiCad library notice {name} not found at {original}')
    copied = sorted(set(copied))
    (target / 'NOTICE.md').write_text(notice_markdown(copied, overrides, sorted(custom), sorted(boxes), notice_text),
                                      encoding='utf-8')
    return dict(libraries=sorted(libs), copied=copied, custom=sorted(custom), models=sorted(boxes),
                overrides=overrides, parts=len(selected), issues=issues, warnings=warnings)


def main(argv=None) -> int:
    """CLI: report availability and pad numbers of Lib:Name ids, or validate a parts JSON's pad/net mapping."""
    parser = argparse.ArgumentParser(description='Check installed footprints and pad/net mappings.')
    parser.add_argument('ids', nargs='*', help='footprint ids such as Package_SO:SOIC-8_3.9x4.9mm_P1.27mm')
    parser.add_argument('--circuit', type=Path, help='parts JSON (V1 circuit.json format) to validate')
    parser.add_argument('--board', help='only parts whose "board" key matches')
    parser.add_argument('--source', type=Path,
                        help='root holding <Lib>.pretty folders, e.g. a project libraries/ directory (default: installed KiCad library)')
    args = parser.parse_args(argv)
    for footprint in args.ids:
        lib, name = footprint.split(':', 1)
        print(footprint, ' '.join(footprint_pads(lib, name, args.source)) if footprint_available(lib, name, args.source) else 'MISSING')
    if args.circuit:
        issues = validate_pad_mapping(json.loads(args.circuit.read_text(encoding='utf-8-sig')), source=args.source, board=args.board)
        print('\n'.join(issues) or 'pad/net mapping consistent')
        return 1 if issues else 0
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
