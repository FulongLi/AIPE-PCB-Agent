"""Parametrised hierarchical KiCad schematic and project writer for the shared AIPE part model.

Generalises generate_buck_schematic.py without referring to any converter: generate_project(spec)
turns an ordered page map plus parts in the V1 model format (ref, value, footprint, nets, page,
kind, pins, ...) into <name>.kicad_sch, one sheet per page with "<page>_2" continuation sheets
instead of a page-full error, a project symbol library holding one explicitly pinned symbol per
part, sym-lib-table, <name>.kicad_pro (net classes, netclass_patterns, board design rules), an
optional <name>.kicad_dru and design/schematic_mapping.json (symbol paths and placement for the
board generator).

Deterministic without KiCad: every uuid is uuid5 of a path-like name, placement is a
left-to-right / top-to-bottom flow on the 1.27 mm connection grid, symbols for R, C, ICs,
connectors, test points, diodes with non-library pin names and FET pinouts without a library
counterpart are generated with explicit pin numbers, names and electrical types, and
analyse_connectivity() applies KiCad's default ERC pin matrix to the model before any file is
written. Official Transistor_FET / Device symbols are copied from the installed KiCad library
when kicad-cli can be found; otherwise generated symbols are substituted and reported.

Requires native KiCad: ERC (automation.kicad_tools.run_check), symbol-library resolution,
footprint-link checks (KiCad 10 warns for every footprint whose library is not in a project or
global fp-lib-table, so a project is only ERC-clean together with its footprint libraries) and
netlist export. A generated project has no CAD evidence until kicad-cli has been run on it; the
pre-checks here approximate, never replace, that run.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import textwrap
from collections import Counter, defaultdict
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Callable

from automation.kicad_tools.native_schematic import Schematic, extract_symbol, parse, pins, quote, uid
from automation.kicad_tools import schematic_presentation as sp
from automation.kicad_tools import schematic_wiring as sw
from automation.setup.detect_kicad import find_kicad_cli

GRID = 1.27
PAPER = {'A4': (297.0, 210.0), 'A3': (420.0, 297.0), 'A2': (594.0, 420.0), 'A1': (841.0, 594.0), 'A0': (1189.0, 841.0)}
PIN_TYPES = ('input', 'output', 'bidirectional', 'tri_state', 'passive', 'free', 'unspecified',
             'power_in', 'power_out', 'open_collector', 'open_emitter', 'no_connect')
# KiCad 10 default ERC pin matrix (project erc.pin_map); rows and columns follow PIN_TYPES.
PIN_MATRIX = ((0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 2), (0, 2, 0, 1, 0, 0, 1, 0, 2, 2, 2, 2),
              (0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 2), (0, 1, 0, 0, 0, 0, 1, 1, 2, 1, 1, 2),
              (0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 2), (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2),
              (1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 2), (0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 2),
              (0, 2, 1, 2, 0, 0, 1, 0, 2, 2, 2, 2), (0, 2, 0, 1, 0, 0, 1, 0, 2, 0, 0, 2),
              (0, 2, 1, 1, 0, 0, 1, 0, 2, 0, 0, 2), (2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2))
SEVERITY = {1: 'warning', 2: 'error'}
MAX_UNIT_PINS = 64
MAX_REPORTED_CONFLICTS = 200
DEFAULT_RULES = {'min_clearance': 0.15, 'min_track_width': 0.15, 'min_via_diameter': 0.55,
                 'min_through_hole_diameter': 0.25, 'min_hole_clearance': 0.25, 'min_copper_edge_clearance': 0.5}
DEFAULT_CLASS = {'name': 'Default', 'clearance': 0.2, 'track_width': 0.25, 'via_diameter': 0.6, 'via_drill': 0.3}
CLASS_KEYS = ('clearance', 'track_width', 'via_diameter', 'via_drill')
FLAG_NOTE = ('PWR_FLAG symbols state supply provenance for ERC; they do not prove voltage, '
             'current capacity or protection.')
FET_ROLES = {'G': 'G', 'GATE': 'G', 'D': 'D', 'DRAIN': 'D', 'S': 'S', 'SOURCE': 'S', 'KS': 'K', 'SK': 'K',
             'DS': 'K', 'SS': 'K', 'KELVIN': 'K', 'KELVINSOURCE': 'K', 'DRIVERSOURCE': 'K', 'SENSE': 'K'}
NAME_SYNONYMS = {'CATHODE': 'K', 'C': 'K', 'ANODE': 'A', **FET_ROLES}
FLAG_SYMBOL = 'PWR_FLAG'
FLAG_DEFINITION = f'''(symbol "{FLAG_SYMBOL}" (power) (pin_numbers (hide yes)) (pin_names (offset 0) (hide yes)) (in_bom no) (on_board no)
  (property "Reference" "#FLG" (at 0 1.905 0) (hide yes) (effects (font (size 1.27 1.27))))
  (property "Value" "PWR_FLAG" (at 0 3.81 0) (hide yes) (effects (font (size 1.27 1.27))))
  (property "Footprint" "" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
  (property "Datasheet" "" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))
  (symbol "{FLAG_SYMBOL}_0_1" (polyline (pts (xy 0 0) (xy 0 1.27) (xy -1.016 1.905) (xy 0 2.54) (xy 1.016 1.905) (xy 0 1.27)) (stroke (width 0) (type default)) (fill (type none))))
  (symbol "{FLAG_SYMBOL}_1_1" (pin power_out line (at 0 0 90) (length 0)
    (name "pwr" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))))'''


@dataclass
class ProjectSpec:
    """Inputs of generate_project(); a plain dict with the same keys is accepted everywhere."""
    name: str
    title: str
    kicad_dir: Path
    design_dir: Path
    pages: dict
    parts: list
    revision: str = 'V2'
    comment: str = 'AI-GENERATED ENGINEERING PROTOTYPE - HUMAN REVIEW REQUIRED'
    flag_nets: list = field(default_factory=list)
    flag_page: str | None = None
    header_lines: list = field(default_factory=list)
    page_notes: dict = field(default_factory=dict)
    net_classes: list = field(default_factory=list)
    design_rules: dict = field(default_factory=dict)
    dru_text: str | None = None
    unit_grouping: Callable | None = None
    paper: str = 'A3'
    library: str = 'AIPE'
    board: str | None = None
    symbol_overrides: dict = field(default_factory=dict)
    auto_flag_power_nets: bool = False
    fp_lib_table: dict | None = None
    mapping_name: str = 'schematic_mapping.json'
    presentation: dict | str | None = None  # None/'legacy' = V2 drawing; dict/'wired' = schematic_presentation (V2.1)


def num(value: float) -> str:
    """Format a millimetre coordinate without float noise (114.30000000000001 -> 114.3)."""
    value = round(value, 4)
    return str(int(value)) if value == int(value) else repr(value)


def snap(value: float) -> float:
    """Round onto the 1.27 mm connection grid that KiCad's endpoint_off_grid ERC check expects."""
    return round(round(value / GRID) * GRID, 4)


def reference_prefix(ref: str) -> str:
    """Alphabetic reference prefix ('TP7' -> 'TP', '#FLG1' -> '#FLG')."""
    return re.match(r'[A-Za-z#]*', ref).group(0) or ref[:1]


def pin_key(number: str):
    """Sort key placing numeric pad numbers first in numeric order ('2' before '10', then 'A1')."""
    match = re.fullmatch(r'(\d+)([A-Za-z]*)', number)
    return (0, int(match.group(1)), match.group(2)) if match else (1, 0, number)


def normalise_pin_name(name: str, number: str) -> str:
    """Canonical pin role name; empty when the pin is unnamed or named after its number."""
    text = re.sub(r'[^A-Z0-9]', '', str(name).upper())
    if not text or text == str(number).upper():
        return ''
    return NAME_SYNONYMS.get(text, NAME_SYNONYMS.get(re.sub(r'\d', '', text), text))


def kicad_data_root() -> Path | None:
    """Installed KiCad share directory (AIPE_KICAD_DATA override), or None when kicad-cli is absent."""
    override = os.environ.get('AIPE_KICAD_DATA')
    if override:
        return Path(override)
    try:
        cli = find_kicad_cli()
    except FileNotFoundError:
        return None
    return cli.parent.parent / 'share/kicad' if cli else None


def coerce_spec(spec) -> ProjectSpec:
    """Return a validated ProjectSpec from a ProjectSpec or dict; raise ValueError on model errors.

    Part dicts are copied and normalised (string pad numbers, default passive pins, str values), so
    one shared model can feed several projects; a ProjectSpec instance itself is updated in place.
    """
    if isinstance(spec, dict):
        unknown = set(spec) - {f.name for f in fields(ProjectSpec)}
        if unknown:
            raise ValueError(f'Unknown spec keys: {sorted(unknown)}')
        spec = ProjectSpec(**spec)
    if not spec.name or re.search(r'[\\/:*?"<>|\s]', spec.name):
        raise ValueError(f'Project name must be a plain file basename: {spec.name!r}')
    spec.kicad_dir, spec.design_dir = Path(spec.kicad_dir), Path(spec.design_dir)
    if not spec.pages:
        raise ValueError('At least one page is required')
    spec.pages = {str(k): str(v) for k, v in dict(spec.pages).items()}
    if spec.paper not in PAPER:
        raise ValueError(f'Unsupported paper {spec.paper!r}; choose from {sorted(PAPER)}')
    spec.flag_page = spec.flag_page or list(spec.pages)[-1]
    if spec.flag_page not in spec.pages:
        raise ValueError(f'flag_page {spec.flag_page!r} is not a page')
    seen, parts = set(), []
    for original in spec.parts:
        part = dict(original)  # normalised copy; the shared model stays untouched
        for key in ('ref', 'footprint', 'nets', 'page', 'kind'):
            if key not in part:
                raise ValueError(f'Part {part.get("ref", "?")!r} lacks {key!r}')
        if part['ref'] in seen:
            raise ValueError(f'Duplicate reference {part["ref"]!r}')
        seen.add(part['ref'])
        part['nets'] = {str(k): v for k, v in part['nets'].items()}
        declared = original.get('pins') or {k: dict(name=k, type='passive') for k in part['nets']}
        part['pins'] = {str(k): dict(v) for k, v in declared.items()}
        if set(part['pins']) != set(part['nets']):
            raise ValueError(f'{part["ref"]}: pins {sorted(set(part["pins"]) ^ set(part["nets"]))} are not declared on both nets and pins')
        for n, pin in part['pins'].items():
            pin['name'] = str(pin.get('name') or n)
            pin['type'] = pin.get('type') or 'passive'
            if pin['type'] not in PIN_TYPES:
                raise ValueError(f'{part["ref"]} pin {n}: unknown electrical type {pin["type"]!r}')
        part['value'] = str(part.get('value') or '')
        if part['footprint'] and ':' not in part['footprint']:
            raise ValueError(f'{part["ref"]}: footprint must be "Library:Name", got {part["footprint"]!r}')
        parts.append(part)
    spec.parts = parts
    classes = [dict(c) for c in spec.net_classes]
    if not any(c.get('name') == 'Default' for c in classes):
        classes.insert(0, dict(DEFAULT_CLASS))
    names = [c.get('name') for c in classes]
    if len(set(names)) != len(names) or not all(names):
        raise ValueError(f'Net class names must be unique and non-empty: {names}')
    for c in classes:
        missing = [k for k in CLASS_KEYS if not isinstance(c.get(k), (int, float))]
        if missing:
            raise ValueError(f'Net class {c["name"]!r} lacks numeric {missing}')
        c['nets'] = [str(p) for p in c.get('nets', [])]
    spec.net_classes = classes
    spec.presentation = sp.coerce_presentation(spec.presentation)
    return spec


def default_unit_grouping(part: dict) -> list[list[str]]:
    """V1 heuristic: DSP pins split into supply / analog / connected / unused units, one unit otherwise.

    Any group larger than MAX_UNIT_PINS is chunked so a unit always fits on a sheet.
    """
    numbers = sorted(part['pins'], key=pin_key)
    if part.get('amplifier_channels'):
        groups = [[str(c[k]) for k in ('positive', 'negative', 'output')] for c in part['amplifier_channels']]
        used = {n for g in groups for n in g}
        remaining = [n for n in numbers if n not in used]
        return groups + ([remaining] if remaining else [])
    if part['kind'] == 'DSP':
        groups = [[], [], [], []]
        for n in numbers:
            name = part['pins'][n]['name'].upper()
            if name.startswith(('VDD', 'VSS', 'VCC', 'GND', 'AVDD', 'AVSS', 'DVDD', 'DVSS')):
                groups[0].append(n)
            elif name.startswith(('ADC', 'AIN')):
                groups[1].append(n)
            elif part['nets'][n] is not None:
                groups[2].append(n)
            else:
                groups[3].append(n)
    else:
        groups = [numbers]
    chunked = []
    for group in groups:
        chunked.extend(group[i:i + MAX_UNIT_PINS] for i in range(0, len(group), MAX_UNIT_PINS))
    return chunked or [[]]


def fet_roles(part: dict) -> dict | None:
    """Map pad number -> G/D/S/K when the pin names describe a single MOSFET; None otherwise."""
    roles = {}
    for n, pin in part['pins'].items():
        role = FET_ROLES.get(re.sub(r'[^A-Z]', '', str(pin['name']).upper()))
        if not role:
            return None
        roles[n] = role
    counts = Counter(roles.values())
    if counts['G'] != 1 or counts['D'] < 1 or counts['S'] < 1 or counts['K'] > 1:
        return None
    return roles


def official_candidates(part: dict, spec: ProjectSpec) -> list[tuple[str, str]]:
    """Installed-library symbols worth trying for a part, most specific first ([] = generate)."""
    override = part.get('symbol') or spec.symbol_overrides.get(part['ref']) or spec.symbol_overrides.get(part['kind'])
    if override:
        return [tuple(override.split(':', 1))]
    kind, count = part['kind'], len(part['pins'])
    if kind == 'Q':
        roles = fet_roles(part)
        if not roles:
            return []
        order = ''.join(roles[n] for n in sorted(part['pins'], key=pin_key))
        text = ' '.join(str(part.get(k, '')) for k in ('value', 'mpn', 'note')).upper()
        family = 'Q_PMOS_' if re.search(r'PMOS|P-CH|P-CHANNEL', text) else 'Q_NMOS_'
        return [('Transistor_FET', family + order), ('Transistor_FET', family + order.replace('K', 'S'))]
    if kind == 'L' and count == 2:
        return [('Device', 'L')]
    if kind == 'D' and count == 2:
        return [('Device', diode_variant(part))]
    if spec.presentation and count == 2 and kind in ('R', 'C'):
        # wired style only (the legacy drawing keeps its generated glyphs byte for byte): compact Device symbols
        if kind == 'R':
            return [('Device', 'R')]
        polar = ':CP_' in part['footprint'] or 'POLAR' in str(part.get('note', '')).upper() or 'polymer' in str(part.get('value', '')).lower()
        return [('Device', 'C_Polarized' if polar else 'C')]
    if count == 2 and (kind in ('F', 'FUSE') or (kind == 'passive' and reference_prefix(part['ref']) == 'F')):
        return [('Device', 'Fuse')]
    return []


def diode_variant(part: dict) -> str:
    """Device-library diode symbol matching the part description (TVS, Zener, Schottky or plain)."""
    text = ' '.join(str(part.get(k, '')) for k in ('value', 'mpn', 'note')).upper()
    names = {normalise_pin_name(p['name'], n) for n, p in part['pins'].items()}
    if 'TVS' in text or re.search(r'\b(SM[ABCDF]J|1\.5KE|P6KE|5\.0SMDJ)', text):
        return 'D_TVS' if ('BIDIR' in text or names == {'A1', 'A2'}) else 'D_Zener'
    if 'ZENER' in text or re.search(r'\bBZ[XTV]', text):
        return 'D_Zener'
    if 'SCHOTTKY' in text or 'SIC' in text:
        return 'D_Schottky'
    return 'D'


def pin_compatible(model: dict, official: dict) -> bool:
    """True when the model's name and type for a pad agree with (or do not contradict) a library pin."""
    if model['type'] != official['type']:
        return False
    a = normalise_pin_name(model['name'], official['number'])
    b = normalise_pin_name(official['name'], official['number'])
    return not a or not b or a == b


class _Library:
    """Cached access to installed KiCad symbol libraries (None root means no library available)."""

    def __init__(self, root: Path | None):
        self.root = root

    def extract(self, library: str, original: str) -> str | None:
        if not self.root:
            return None
        path = self.root / 'symbols' / (library + '.kicad_sym')
        if not path.is_file():
            return None
        try:
            return extract_symbol(path, original)
        except ValueError:
            return None


def official_symbol(part: dict, candidates: list, library: _Library, name: str):
    """(definition, extents, source) for the first candidate whose pins match the part, else None."""
    for lib, original in candidates:
        definition = library.extract(lib, original)
        if not definition:
            continue
        official = {p['number']: p for p in pins(definition)}
        if set(official) != set(part['pins']) or not all(pin_compatible(part['pins'][n], official[n]) for n in official):
            continue
        definition = definition.replace('"' + original, '"' + name)
        width = max(10.16, 2 * max(abs(p['x']) for p in official.values()) + 5.08)
        height = max(10.16, 2 * max(abs(p['y']) for p in official.values()) + 5.08)
        return definition, [(width, height)], f'{lib}:{original}'
    return None


def pin_sexpr(ptype: str, x: float, y: float, angle: int, length: float, name: str, number: str, size: float = 1.0) -> str:
    """One library pin with explicit electrical type, position, name and number."""
    return (f'(pin {ptype} line (at {num(x)} {num(y)} {angle}) (length {num(length)}) '
            f'(name {quote(name)} (effects (font (size {size} {size})))) '
            f'(number {quote(number)} (effects (font (size {size} {size})))))')


def _line(x1, y1, x2, y2, width=0.254):
    return (f'(polyline (pts (xy {num(x1)} {num(y1)}) (xy {num(x2)} {num(y2)})) '
            f'(stroke (width {width}) (type default)) (fill (type none)))')


def _path(points, fill='none'):
    pts = ' '.join(f'(xy {num(x)} {num(y)})' for x, y in points)
    return f'(polyline (pts {pts}) (stroke (width 0) (type default)) (fill (type {fill})))'


def _header(name: str, part: dict, hide_names: bool = False) -> str:
    return (f'(symbol {quote(name)} (pin_names (offset 0.508){" (hide yes)" if hide_names else ""}) (in_bom yes) (on_board yes)\n'
            f'  (property "Reference" {quote(reference_prefix(part["ref"]))} (at 0 7.62 0) (effects (font (size 1.27 1.27))))\n'
            f'  (property "Value" {quote(part["value"])} (at 0 5.08 0) (effects (font (size 1.27 1.27))))\n'
            f'  (property "Footprint" {quote(part["footprint"])} (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))\n'
            f'  (property "Datasheet" "" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))\n')


def fet_symbol(part: dict, roles: dict, name: str):
    """Generated MOSFET glyph with the model's pad numbers: G, D, S plus optional Kelvin source and tab drain.

    Returns None when the pinout is not G/D/S[/K][/second D]; the caller then uses a rectangle.
    """
    counts = Counter(roles.values())
    if counts['S'] != 1 or counts['D'] > 2 or len(roles) > 5:
        return None
    position = {'G': (-5.08, 0, 0), 'D': (2.54, 5.08, 270), 'S': (2.54, -5.08, 90), 'K': (-5.08, -2.54, 0), 'D2': (-5.08, 2.54, 0)}
    graphics = [_line(-2.54, 0, 0.254, 0, 0), _line(0.254, 1.905, 0.254, -1.905), _line(0.762, 2.286, 0.762, 1.27),
                _line(0.762, 0.508, 0.762, -0.508), _line(0.762, -1.27, 0.762, -2.286),
                _path([(2.54, 2.54), (2.54, 1.778), (0.762, 1.778)]), _path([(2.54, -2.54), (2.54, -1.778), (0.762, -1.778)]),
                _path([(2.54, 0), (0.762, 0)]), _path([(1.016, 0), (2.032, 0.381), (2.032, -0.381), (1.016, 0)], 'outline'),
                '(circle (center 1.651 0) (radius 2.794) (stroke (width 0.254) (type default)) (fill (type none)))']
    drains = 0
    for n in sorted(roles, key=pin_key):
        role = roles[n]
        if role == 'D':
            drains += 1
            role = 'D2' if drains == 2 else 'D'
        x, y, angle = position[role]
        if role == 'K':
            graphics.append(_path([(-2.54, -2.54), (-2.54, -3.175), (2.54, -3.175)]))
        if role == 'D2':
            graphics.append(_path([(-2.54, 2.54), (-2.54, 3.175), (2.54, 3.175)]))
        graphics.append(pin_sexpr(part['pins'][n]['type'], x, y, angle, 2.54, part['pins'][n]['name'], n, 1.27))
    definition = _header(name, part, hide_names=True) + f'  (symbol "{name}_1_1" {chr(10).join(graphics)}))'
    return definition, [(15.24, 15.24)], 'generated:fet'


def diode_symbol(part: dict, name: str):
    """Generated diode glyph (anode left, cathode right) honouring the model's own pad numbering."""
    roles = {n: normalise_pin_name(p['name'], n) for n, p in part['pins'].items()}
    if sorted(roles.values()) != ['A', 'K']:
        return None
    graphics = [_path([(-1.27, 1.27), (1.27, 0), (-1.27, -1.27), (-1.27, 1.27)]), _line(1.27, 1.27, 1.27, -1.27)]
    for n, role in roles.items():
        x, angle = (-3.81, 0) if role == 'A' else (3.81, 180)
        graphics.append(pin_sexpr(part['pins'][n]['type'], x, 0, angle, 2.54, part['pins'][n]['name'], n, 1.27))
    definition = _header(name, part, hide_names=True) + f'  (symbol "{name}_1_1" {chr(10).join(graphics)}))'
    return definition, [(12.7, 10.16)], 'generated:diode'


def generic_symbol(part: dict, groups: list, name: str, pin_order: Callable | None = None):
    """V1-style rectangular (or small R/C glyph) multi-unit symbol with every model pin placed and typed.

    `pin_order(part, number)` (optional) re-sorts the pins *within each side* of a unit (stable, so pin-number order is
    kept inside equal keys); the wired drawing uses it to make same-rail pins adjacent so they share one bus.
    """
    bodies, extents = [], []
    for unit, numbers in enumerate(groups, 1):
        numbers = sorted(numbers, key=pin_key)
        small = len(numbers) <= 2
        half = math.ceil(len(numbers) / 2)
        if pin_order is not None and not small:
            numbers = sorted(numbers[:half], key=lambda n: pin_order(part, n)) + sorted(numbers[half:], key=lambda n: pin_order(part, n))
        height = max(5.08, (half + 1) * 2.54)
        width = 5.08 if small else 38.1
        extents.append((width, height))
        if small and part['kind'] == 'C':
            graphics = [_line(-0.8, -2.54, -0.8, 2.54), _line(0.8, -2.54, 0.8, 2.54), _line(-2.54, 0, -0.8, 0), _line(0.8, 0, 2.54, 0)]
            if ':CP_' in part['footprint'] or 'POLAR' in str(part.get('note', '')).upper():
                graphics += [_line(-2.0, 3.3, -2.0, 4.7), _line(-2.7, 4, -1.3, 4)]
        elif small and part['kind'] == 'R':
            graphics = ['(rectangle (start -2.54 1.27) (end 2.54 -1.27) (stroke (width 0.254) (type default)) (fill (type none)))']
        else:
            graphics = [f'(rectangle (start {num(-width / 2)} {num(height / 2)}) (end {num(width / 2)} {num(-height / 2)}) '
                        '(stroke (width 0.254) (type default)) (fill (type background)))']
        for index, n in enumerate(numbers):
            right = index >= half
            row = index - half if right else index
            y = 0 if small else round(height / 2 - 2.54 * (row + 1), 4)
            x = round((width / 2 + 5.08) * (1 if right else -1), 4)
            pin = part['pins'][n]
            graphics.append(pin_sexpr(pin['type'], x, y, 180 if right else 0, 5.08, '~' if small else pin['name'], n))
        bodies.append(f'  (symbol "{name}_{unit}_1" {chr(10).join(graphics)})')
    return _header(name, part) + '\n'.join(bodies) + ')', extents, 'generated:rectangle'


def symbol_for(part: dict, spec: ProjectSpec, library: _Library, grouping: Callable, pin_order: Callable | None = None):
    """(symbol name, library definition, per-unit (width, height) extents, source) for a part."""
    name = 'Sym_' + part['ref']
    groups = [list(map(str, g)) for g in grouping(part)]
    if sorted(n for g in groups for n in g) != sorted(part['pins']):
        raise ValueError(f'{part["ref"]}: unit grouping does not partition the pins')
    groups = [g for g in groups if g] or [[]]
    if part.get('amplifier_channels'):
        return (name, *amplifier_symbol(part, groups, name))
    if len(groups) == 1:
        result = official_symbol(part, official_candidates(part, spec), library, name)
        if result:
            return (name, *result)
        if part['kind'] == 'Q':
            roles = fet_roles(part)
            result = fet_symbol(part, roles, name) if roles else None
            if result:
                return (name, *result)
        if part['kind'] == 'D' and len(part['pins']) == 2:
            result = diode_symbol(part, name)
            if result:
                return (name, *result)
    return (name, *generic_symbol(part, groups, name, pin_order))


def amplifier_symbol(part: dict, groups: list, name: str):
    """Explicit-pin multi-channel analogue triangles, with a separate supply unit.

    Opt-in metadata prevents guessing a manufacturer's pinout from the part name.
    Every original pin remains present once, including supply and unused pins.
    """
    units=[];extents=[]
    for i,group in enumerate(groups,1):
        if i <= len(part['amplifier_channels']):
            ch={k:str(v) for k,v in part['amplifier_channels'][i-1].items()}
            if set(group) != set(ch.values()):raise ValueError('Amplifier channel grouping mismatch')
            graphics=[_path([(-5.08,5.08),(-5.08,-5.08),(5.08,0),(-5.08,5.08)])]
            for role,xy in [('positive',(-7.62,2.54,0)),('negative',(-7.62,-2.54,0)),('output',(7.62,0,180))]:
                n=ch[role];p=part['pins'][n]
                graphics.append(pin_sexpr(p['type'],*xy,2.54,'+' if role=='positive' else '-' if role=='negative' else p['name'],n))
            extents.append((20.32,15.24))
        else:
            h=max(7.62,2.54*(len(group)+1));graphics=[f'(rectangle (start -5.08 {num(h/2)}) (end 5.08 {num(-h/2)}) (stroke (width 0.254) (type default)) (fill (type background)))']
            for k,n in enumerate(group):
                p=part['pins'][n]
                graphics.append(pin_sexpr(p['type'],-7.62,snap((len(group)-1)*1.27-k*2.54),0,2.54,p['name'],n))
            extents.append((20.32,h+5.08))
        units.append(f'(symbol "{name}_{i}_1" '+ '\n'.join(graphics)+')')
    return _header(name,part)+'\n'.join(units)+')',extents,'generated:explicit-analog-channels'


def analyse_connectivity(parts: list, flag_nets=()) -> dict:
    """Deterministic pre-check of the model against KiCad's default ERC pin matrix.

    Returns undriven_power_nets (power_in without power_out or PWR_FLAG -> power_pin_not_driven),
    pin_conflicts (pairs KiCad would warn about or reject -> pin_to_pin, PWR_FLAGs counted as
    power_out), single_pin_nets (KiCad 10 reports these as isolated_pin_label warnings) and
    no_connect_pins_with_nets (-> no_connect_connected). Empty lists mean the model is consistent;
    native ERC is the evidence.
    """
    by_net = defaultdict(list)
    nc_with_net = []
    for part in parts:
        for n, net in part['nets'].items():
            if net is None:
                continue
            ptype = part['pins'][n]['type']
            if ptype == 'no_connect':
                nc_with_net.append(f'{part["ref"]}.{n}')
            by_net[net].append((part['ref'], n, ptype))
    for i, net in enumerate(flag_nets, 1):
        by_net[net].append((f'#FLG{i}', '1', 'power_out'))
    undriven = sorted(net for net, items in by_net.items()
                      if any(t == 'power_in' for *_, t in items) and not any(t == 'power_out' for *_, t in items))
    conflicts, total = [], 0
    for net, items in sorted(by_net.items()):
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                level = PIN_MATRIX[PIN_TYPES.index(items[i][2])][PIN_TYPES.index(items[j][2])]
                if level:
                    total += 1
                    if len(conflicts) < MAX_REPORTED_CONFLICTS:
                        conflicts.append(dict(net=net, a=f'{items[i][0]}.{items[i][1]}', b=f'{items[j][0]}.{items[j][1]}',
                                              severity=SEVERITY[level]))
    return dict(undriven_power_nets=undriven, pin_conflicts=conflicts, pin_conflict_count=total,
                single_pin_nets=sorted(net for net, items in by_net.items() if len(items) == 1),
                no_connect_pins_with_nets=sorted(nc_with_net))


def project_settings(name: str, net_classes: list, design_rules: dict | None = None, drc_severities: dict | None = None) -> dict:
    """KiCad 10 .kicad_pro content: net classes with netclass_patterns and board design rules."""
    classes, patterns = [], []
    for index, c in enumerate(net_classes):
        default = c['name'] == 'Default'
        classes.append({'bus_width': 12, 'clearance': c['clearance'], 'diff_pair_gap': c.get('diff_pair_gap', 0.25),
                        'diff_pair_via_gap': c.get('diff_pair_via_gap', 0.25), 'diff_pair_width': c.get('diff_pair_width', c['track_width']),
                        'line_style': 0, 'microvia_diameter': c.get('microvia_diameter', 0.3), 'microvia_drill': c.get('microvia_drill', 0.1),
                        'name': c['name'], 'pcb_color': 'rgba(0, 0, 0, 0.000)',
                        'priority': 2147483647 if default else c.get('priority', index),
                        'schematic_color': 'rgba(0, 0, 0, 0.000)', 'track_width': c['track_width'],
                        'via_diameter': c['via_diameter'], 'via_drill': c['via_drill'], 'wire_width': 6})
        patterns.extend({'netclass': c['name'], 'pattern': p} for p in c.get('nets', []))
    design = {'rules': {**DEFAULT_RULES, **(design_rules or {})}}
    if drc_severities:
        design['rule_severities'] = dict(drc_severities)
    return {'board': {'3dviewports': [], 'design_settings': design, 'layer_presets': [], 'viewports': []},
            'boards': [], 'cvpcb': {'equivalence_files': []},
            'libraries': {'pinned_footprint_libs': [], 'pinned_symbol_libs': []},
            'meta': {'filename': name + '.kicad_pro', 'version': 1},
            'net_settings': {'classes': classes, 'meta': {'version': 4}, 'net_colors': None,
                             'netclass_assignments': None, 'netclass_patterns': patterns},
            'pcbnew': {'last_paths': {'gencad': '', 'idf': '', 'netlist': '', 'plot': '', 'specctra_dsn': '', 'step': '', 'svg': '', 'vrml': ''},
                       'page_layout_descr_file': ''},
            'schematic': {'legacy_lib_dir': '', 'legacy_lib_list': []}, 'sheets': [], 'text_variables': {}}


def normalise_dru(text: str) -> str:
    """Custom design-rule text with a (version 1) header; ValueError when the s-expressions are unbalanced."""
    text = text.strip()
    if not text.startswith('(version'):
        text = '(version 1)\n' + text
    parse('(' + text + ')')
    return text + '\n'


def root_grid(count: int, paper: str, top: float):
    """Root-sheet paper and sheet-symbol positions for `count` sub-sheets (grows the paper when needed)."""
    papers = list(PAPER)
    for name in papers[papers.index(paper):]:
        width, height = PAPER[name]
        columns = max(1, int((width - 22.86 - 12.7) // 124.46))
        rows = max(1, int((height - top - 12.7) // 35.56))
        if columns * rows >= count:
            return name, [(snap(22.86 + (i % columns) * 124.46), snap(top + (i // columns) * 35.56)) for i in range(count)]
    raise ValueError(f'{count} sheets do not fit on the root sheet of any supported paper size')


class _Generator:
    def __init__(self, spec: ProjectSpec):
        self.spec = spec
        self.root = Schematic(spec.name, spec.title, spec.paper, revision=spec.revision, comment=spec.comment)
        self.sheets: list[dict] = []
        self.definitions: dict[str, str] = {}
        self.paths, self.placement, self.symbols, self.flags = {}, {}, {}, []
        width, height = PAPER[spec.paper]
        self.left, self.top, self.right, self.bottom = 6.35, 33.02, width - 12.7, height - 30.0

    def new_sheet(self, key: str, page: str, title: str, note: str) -> dict:
        sheet_id = uid(self.spec.name + '/' + key + '/sheet')
        instance_path = '/' + self.root.root_uuid + '/' + sheet_id
        sch = Schematic(self.spec.name + '/' + key, title, self.spec.paper, project_name=self.spec.name,
                        instance_path=instance_path, revision=self.spec.revision, comment=self.spec.comment)
        sch.text(title, 12.7, 16.51, 2)
        if note:
            sch.text(note, 12.7, 22.86, 1)
        self.sheets.append(dict(key=key, page=page, title=title, file=key + '.kicad_sch', uuid=sheet_id,
                                instance_path=instance_path, sch=sch))
        return self.sheets[-1]

    def place_part(self, part: dict, flow: '_Flow', library: _Library, grouping: Callable, fallbacks: dict) -> None:
        name, definition, extents, source = symbol_for(part, self.spec, library, grouping)
        if source.startswith('generated') and (part['kind'] in ('Q', 'L', 'D') or official_candidates(part, self.spec)):
            fallbacks[part['ref']] = source
        self.definitions[name] = definition
        lib_id = f'{self.spec.library}:{name}'
        self.symbols[part['ref']] = dict(lib_id=lib_id, source=source, units=len(extents))
        for unit, (width, height) in enumerate(extents, 1):
            info = pins(definition, unit)
            sides = [[len(part['nets'][p['number']] or '') for p in info if p['x'] <= 0],
                     [len(part['nets'][p['number']] or '') for p in info if p['x'] > 0]]
            labels = sum(max(side, default=0) * 1.1 + 5.08 for side in sides)
            cell_width = max(63.5, math.ceil((width + 15.24 + labels) / 2.54) * 2.54)
            cell_height = max(27.94, snap(height + 22.86))
            sch, x, y = flow.place(cell_width, cell_height)
            center_x, center_y = snap(x + cell_width / 2), snap(y + height / 2 + 7.62)
            in_bom = bool(part.get('in_bom', part['kind'] not in ('TP', 'H')))
            locations = sch.add_symbol(lib_id, definition, part['ref'], part['value'], part['footprint'], center_x, center_y,
                                       unit, property_y=-height / 2 - 6.35, in_bom=in_bom, on_board=bool(part.get('on_board', True)))
            if unit == 1:
                self.paths[part['ref']] = flow.sheet['instance_path'] + '/' + sch.references[part['ref']]
            for n, point in locations.items():
                point = (round(point[0], 4), round(point[1], 4))
                net = part['nets'][n]
                if net is None:
                    sch.no_connect(point)
                    continue
                right = point[0] > center_x
                end = (round(point[0] + (2.54 if right else -2.54), 4), point[1])
                sch.wire(point, end)
                sch.global_label(net, end, 0 if right else 180)
            self.placement.setdefault(part['ref'], []).append(dict(sheet=flow.sheet['key'], page=part['page'], unit=unit,
                                                                   x=center_x, y=center_y))

    def place_flags(self, flow: '_Flow', nets: list) -> None:
        self.definitions[FLAG_SYMBOL] = FLAG_DEFINITION
        lib_id = f'{self.spec.library}:{FLAG_SYMBOL}'
        for index, net in enumerate(nets, 1):
            cell_width = max(45.72, math.ceil((len(net) * 1.1 + 12.7) / 2.54) * 2.54)
            sch, x, y = flow.place(cell_width, 25.4)
            fx, fy = snap(x + 5.08), snap(y + 12.7)
            points = sch.add_symbol(lib_id, FLAG_DEFINITION, f'#FLG{index}', 'PWR_FLAG', '', fx, fy, in_bom=False, on_board=False)
            point = (round(points['1'][0], 4), round(points['1'][1], 4))
            sch.global_label(net, point)
            self.flags.append(dict(net=net, reference=f'#FLG{index}', sheet=flow.sheet['key'], x=fx, y=fy))


class _Flow:
    """Left-to-right, top-to-bottom cell cursor that opens '<page>_N' sheets instead of overflowing."""

    def __init__(self, gen: _Generator, page: str):
        self.gen, self.page, self.count = gen, page, 0
        self.title = gen.spec.pages[page]
        self.note = gen.spec.page_notes.get(page, '')
        if page == gen.spec.flag_page and gen.spec.flag_nets:
            self.note = (self.note + '\n' if self.note else '') + FLAG_NOTE
        self.sheet = None
        self.x = self.y = self.row = 0.0
        self.open()

    def open(self) -> None:
        self.count += 1
        key = self.page if self.count == 1 else f'{self.page}_{self.count}'
        title = self.title if self.count == 1 else f'{self.title} ({self.count})'
        self.sheet = self.gen.new_sheet(key, self.page, title, self.note)
        self.x, self.y, self.row = self.gen.left, self.gen.top, 0.0

    def place(self, cell_width: float, cell_height: float):
        gen = self.gen
        if self.x > gen.left and self.x + cell_width > gen.right:
            self.x, self.y, self.row = gen.left, snap(self.y + self.row), 0.0
        if self.y > gen.top and self.y + cell_height > gen.bottom:
            self.open()
        sch, x, y = self.sheet['sch'], self.x, self.y
        self.x, self.row = snap(self.x + cell_width), max(self.row, cell_height)
        return sch, x, y


def generate_project(spec) -> dict:
    """Write the KiCad project described by `spec` (ProjectSpec or dict) and return a summary.

    Files: <kicad_dir>/<name>.kicad_sch, one <page>.kicad_sch per page plus <page>_N continuation
    sheets, libraries/<library>.kicad_sym, sym-lib-table, <name>.kicad_pro, optional <name>.kicad_dru
    and fp-lib-table, and <design_dir>/<mapping_name>. The summary lists files, sheets, placed and
    skipped parts, official-symbol fallbacks, PWR_FLAGs and analyse_connectivity() diagnostics.
    Deterministic for identical inputs; the result is unverified until kicad-cli ERC has run.
    """
    spec = coerce_spec(spec)
    library = _Library(kicad_data_root())
    grouping = spec.unit_grouping or default_unit_grouping
    gen = _Generator(spec)
    skipped, parts = {}, []
    for part in spec.parts:
        if part['page'] not in spec.pages:
            skipped[part['ref']] = f'page {part["page"]!r} not in this project'
        elif spec.board and part.get('board', spec.board) != spec.board:
            skipped[part['ref']] = f'board {part["board"]!r}'
        else:
            parts.append(part)
    flag_nets = list(spec.flag_nets)
    if spec.auto_flag_power_nets:
        flag_nets += [n for n in analyse_connectivity(parts, flag_nets)['undriven_power_nets'] if n not in flag_nets]
    spec.flag_nets = flag_nets
    diagnostics = analyse_connectivity(parts, flag_nets)
    if spec.presentation:
        return _generate_wired(spec, parts, flag_nets, diagnostics, library, grouping, skipped)
    fallbacks = {}
    for page in spec.pages:
        flow = _Flow(gen, page)
        for part in (p for p in parts if p['page'] == page):
            gen.place_part(part, flow, library, grouping, fallbacks)
        if page == spec.flag_page and flag_nets:
            gen.place_flags(flow, flag_nets)
    kicad_dir, design_dir = spec.kicad_dir, spec.design_dir
    (kicad_dir / 'libraries').mkdir(parents=True, exist_ok=True)
    design_dir.mkdir(parents=True, exist_ok=True)
    root = gen.root
    root.text(spec.comment, 20, 20, 2)
    if spec.header_lines:
        root.text('\n'.join(spec.header_lines), 20, 31, 1.5)
    top = max(63.5, snap(31 + 2.54 * len(spec.header_lines) + 7.62))
    paper, positions = root_grid(len(gen.sheets), spec.paper, top)
    root.paper = paper
    titles = Counter(s['title'] for s in gen.sheets)
    files = []
    for number, (sheet, (sx, sy)) in enumerate(zip(gen.sheets, positions), 2):
        sheet_name = sheet['title'] if titles[sheet['title']] == 1 else f'{sheet["title"]} [{sheet["key"]}]'
        sheet['page_number'] = number
        root.items.append(f'''(sheet (at {num(sx)} {num(sy)}) (size 111.76 25.4) (stroke (width 0.254) (type default))
            (fill (color 0 0 0 0)) (uuid "{sheet['uuid']}")
            (property "Sheetname" {quote(sheet_name)} (at {num(sx)} {num(sy - 1.27)} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
            (property "Sheetfile" {quote(sheet['file'])} (at {num(sx)} {num(sy + 26.67)} 0) (effects (font (size 1.0 1.0)) (justify left top)))
            (instances (project {quote(spec.name)} (path "/{root.root_uuid}" (page "{number}")))))''')
        sheet['sch'].write(kicad_dir / sheet['file'])
        files.append(kicad_dir / sheet['file'])
    root.write(kicad_dir / (spec.name + '.kicad_sch'))
    files.append(kicad_dir / (spec.name + '.kicad_sch'))
    removed_sheets = remove_stale_sheets(kicad_dir, set(spec.pages), files)
    lib_path = kicad_dir / 'libraries' / (spec.library + '.kicad_sym')
    lib_path.write_text('(kicad_symbol_lib (version 20250114) (generator "aipe")\n' + '\n'.join(gen.definitions.values()) + ')\n',
                        encoding='utf-8')
    (kicad_dir / 'sym-lib-table').write_text(
        f'(sym_lib_table (version 7) (lib (name {quote(spec.library)}) (type "KiCad") (uri "${{KIPRJMOD}}/libraries/{spec.library}.kicad_sym") '
        f'(options "") (descr {quote(spec.name + " explicit pin mappings")})))\n', encoding='utf-8')
    files += [lib_path, kicad_dir / 'sym-lib-table']
    pro = kicad_dir / (spec.name + '.kicad_pro')
    pro.write_text(json.dumps(project_settings(spec.name, spec.net_classes, spec.design_rules), indent=2) + '\n', encoding='utf-8')
    files.append(pro)
    if spec.dru_text:
        dru = kicad_dir / (spec.name + '.kicad_dru')
        dru.write_text(normalise_dru(spec.dru_text), encoding='utf-8')
        files.append(dru)
    if spec.fp_lib_table:
        rows = ''.join(f'\n  (lib (name {quote(lib)}) (type "KiCad") (uri {quote(uri)}) (options "") (descr "project footprint library"))'
                       for lib, uri in spec.fp_lib_table.items())
        (kicad_dir / 'fp-lib-table').write_text(f'(fp_lib_table (version 7){rows})\n', encoding='utf-8')
        files.append(kicad_dir / 'fp-lib-table')
    sheets = [{k: v for k, v in s.items() if k != 'sch'} for s in gen.sheets]
    mapping = dict(project=spec.name, generator='automation.kicad_tools.project_schematic', root_uuid=root.root_uuid,
                   paths=gen.paths, placement=gen.placement, sheets=sheets, symbols=gen.symbols, flags=gen.flags,
                   skipped=skipped, symbol_fallbacks=fallbacks, diagnostics=diagnostics,
                   library_root=str(library.root) if library.root else None)
    mapping_path = design_dir / spec.mapping_name
    mapping_path.write_text(json.dumps(mapping, indent=2) + '\n', encoding='utf-8')
    return dict(name=spec.name, root=str(kicad_dir / (spec.name + '.kicad_sch')), project=str(pro), mapping=str(mapping_path),
                files=[str(f) for f in files], sheets=sheets, parts_placed=len(gen.paths), skipped=skipped,
                continuation_sheets=[s['key'] for s in sheets if s['key'] != s['page']], symbol_fallbacks=fallbacks,
                flags=flag_nets, diagnostics=diagnostics, library_root=mapping['library_root'], removed_sheets=removed_sheets)


# --- V2.1 wired presentation --------------------------------------------------------------------------------------

def remove_stale_sheets(kicad_dir: Path, pages, written) -> list[str]:
    """Delete <page>.kicad_sch / <page>_N.kicad_sch files of known pages that this generation did not write.

    A regeneration that needs fewer continuation sheets (or none, in the wired style) must not leave the previous
    run's sheets beside the project: they are not referenced by the root but confuse reviewers and tools.  Only
    files whose stem is a page key of the spec are touched; the root sheet and foreign files are never removed.
    """
    written = {Path(p).resolve() for p in written}
    removed = []
    for path in sorted(Path(kicad_dir).glob('*.kicad_sch')):
        if path.resolve() in written:
            continue
        match = re.fullmatch(r'(.+?)(?:_\d+)?\.kicad_sch', path.name)
        if match and match.group(1) in pages:
            path.unlink()
            removed.append(path.name)
    return removed


def _write_project_files(spec: ProjectSpec, gen: _Generator, root: Schematic, definitions: dict, library: _Library,
                         mapping_extra: dict, fallbacks: dict, skipped: dict, diagnostics: dict, flag_nets: list) -> dict:
    """Shared tail of the wired generator: sheet files, library, tables, project, DRU, mapping and summary."""
    kicad_dir, design_dir = spec.kicad_dir, spec.design_dir
    (kicad_dir / 'libraries').mkdir(parents=True, exist_ok=True)
    design_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for sheet in gen.sheets:
        sheet['sch'].write(kicad_dir / sheet['file'])
        files.append(kicad_dir / sheet['file'])
    root.write(kicad_dir / (spec.name + '.kicad_sch'))
    files.append(kicad_dir / (spec.name + '.kicad_sch'))
    mapping_extra = dict(mapping_extra, removed_sheets=remove_stale_sheets(kicad_dir, set(spec.pages), files))
    lib_path = kicad_dir / 'libraries' / (spec.library + '.kicad_sym')
    lib_path.write_text('(kicad_symbol_lib (version 20250114) (generator "aipe")\n' + '\n'.join(definitions.values()) + ')\n',
                        encoding='utf-8')
    (kicad_dir / 'sym-lib-table').write_text(
        f'(sym_lib_table (version 7) (lib (name {quote(spec.library)}) (type "KiCad") (uri "${{KIPRJMOD}}/libraries/{spec.library}.kicad_sym") '
        f'(options "") (descr {quote(spec.name + " explicit pin mappings")})))\n', encoding='utf-8')
    files += [lib_path, kicad_dir / 'sym-lib-table']
    pro = kicad_dir / (spec.name + '.kicad_pro')
    pro.write_text(json.dumps(project_settings(spec.name, spec.net_classes, spec.design_rules), indent=2) + '\n', encoding='utf-8')
    files.append(pro)
    if spec.dru_text:
        dru = kicad_dir / (spec.name + '.kicad_dru')
        dru.write_text(normalise_dru(spec.dru_text), encoding='utf-8')
        files.append(dru)
    if spec.fp_lib_table:
        rows = ''.join(f'\n  (lib (name {quote(lib)}) (type "KiCad") (uri {quote(uri)}) (options "") (descr "project footprint library"))'
                       for lib, uri in spec.fp_lib_table.items())
        (kicad_dir / 'fp-lib-table').write_text(f'(fp_lib_table (version 7){rows})\n', encoding='utf-8')
        files.append(kicad_dir / 'fp-lib-table')
    sheets = [{k: v for k, v in s.items() if k != 'sch'} for s in gen.sheets]
    mapping = dict(project=spec.name, generator='automation.kicad_tools.project_schematic', root_uuid=root.root_uuid,
                   paths=gen.paths, placement=gen.placement, sheets=sheets, symbols=gen.symbols, flags=gen.flags,
                   skipped=skipped, symbol_fallbacks=fallbacks, diagnostics=diagnostics,
                   library_root=str(library.root) if library.root else None, **mapping_extra)
    mapping_path = design_dir / spec.mapping_name
    mapping_path.write_text(json.dumps(mapping, indent=2) + '\n', encoding='utf-8')
    return dict(name=spec.name, root=str(kicad_dir / (spec.name + '.kicad_sch')), project=str(pro), mapping=str(mapping_path),
                files=[str(f) for f in files], sheets=sheets, parts_placed=len(gen.paths), skipped=skipped,
                continuation_sheets=[s['key'] for s in sheets if s['key'] != s['page']], symbol_fallbacks=fallbacks,
                flags=flag_nets, diagnostics=diagnostics, library_root=mapping['library_root'], **mapping_extra)


def _root_pins(root_plan: dict) -> tuple[list, list]:
    """Sheet pins (with their 5.08 mm stubs) and the global anchor labels of the root sheet."""
    root_pins, root_labels = [], []
    for entry, (sx, sy) in zip(root_plan['entries'], root_plan['positions']):
        key = entry['sheet']['key']
        for side, items in (('left', entry['left']), ('right', entry['right'])):
            for index, (net, shape) in enumerate(items):
                py = snap(sy + 5.08 + 2.54 * index)
                px = sx if side == 'left' else snap(sx + entry['w'])
                stub = snap(px - 5.08) if side == 'left' else snap(px + 5.08)
                root_pins.append(dict(sheet=key, name=net, point=(px, py), side=side, shape=shape, stub=(stub, py)))
                root_labels.append(dict(name=net, point=(stub, py), angle=180 if side == 'left' else 0))
    return root_pins, root_labels


def _generate_wired(spec: ProjectSpec, parts: list, flag_nets: list, diagnostics: dict, library: _Library,
                    grouping: Callable, skipped: dict) -> dict:
    """V2.1 drawing: schematic_presentation plan -> connectivity guard -> KiCad files (one sheet per page)."""
    presentation = spec.presentation
    gen = _Generator(spec)
    fallbacks = {}

    def rail_pin_order(part, number):
        """Supply pins first, signal pins (pin-number order) in the middle, ground-style rails last on every side.

        Consecutive same-rail pins form one bus; a supply symbol at the top of a side and a ground symbol at its
        bottom point into free space instead of into the neighbouring signal lanes (TI reference-schematic order).
        """
        net = part['nets'].get(number)
        info = planner.nets.get(net, {}) if net is not None else {}
        if net is None or info.get('role') != 'rail':
            return (1, '')
        return (2, net) if info.get('down') else (0, net)

    def symbol_for_part(part):
        name, definition, extents, source = symbol_for(part, spec, library, grouping, rail_pin_order)
        if source.startswith('generated') and (part['kind'] in ('Q', 'L', 'D') or (part['kind'] not in ('R', 'C') and official_candidates(part, spec))):
            fallbacks[part['ref']] = source
        gen.definitions[name] = definition
        gen.symbols[part['ref']] = dict(lib_id=f'{spec.library}:{name}', source=source, units=len(extents))
        return name, definition, extents, source

    planner = sp.Planner(spec, parts, presentation, symbol_for_part)
    papers = [p for p in presentation['paper_escalation'] if p in PAPER]
    papers = papers[papers.index(spec.paper):] if spec.paper in papers else [spec.paper] + papers
    plans = []
    for page in spec.pages:
        page_parts = [p for p in parts if p['page'] == page]
        is_flag_page = page == spec.flag_page and bool(flag_nets)
        if not page_parts and not planner.flags_for_page(page, flag_nets, is_flag_page):
            continue
        note = spec.page_notes.get(page, '')
        if is_flag_page:
            note = (note + ' ' if note else '') + FLAG_NOTE
        note_lines = textwrap.wrap(note, presentation['note_width']) if note else []
        header_height = 2.54 + len(note_lines) * presentation['note_size'] * 1.6 + 5.08
        planned = planner.plan_page(page, page_parts, flag_nets, is_flag_page, papers, PAPER, header_height)
        paper, positions = planned['paper'], planned['positions']
        width = PAPER[paper][0]
        texts = [dict(kind='title', text=spec.pages[page], x=snap(width / 2), y=15.24),
                 dict(kind='note', text='\n'.join(note_lines), x=20.32, y=22.86)]
        plan = sp.route_sheet(planner, page, positions, paper, PAPER, texts)
        plan.title = spec.pages[page]
        plan.counts['layout_variant'] = planned['variant']
        plans.append(plan)
    root = gen.root
    root.text(spec.comment, 20, 20, 2)
    if spec.header_lines:
        root.text('\n'.join(spec.header_lines), 20, 31, 1.5)
    top = max(63.5, snap(31 + 2.54 * len(spec.header_lines) + 7.62))
    root_plan = sp.plan_root([dict(key=plan.key, ports=plan.ports) for plan in plans], planner, PAPER, spec.paper, top)
    root.paper = root_plan['paper']
    root_pins, root_labels = _root_pins(root_plan)
    # connectivity guard before any file is written
    root_wiring = sw.SheetWiring()
    root_wiring.segments = [sw.Segment(pin['name'], pin['point'], pin['stub']) for pin in root_pins]
    root_wiring.labels = [dict(kind='global', name=l['name'], point=l['point']) for l in root_labels] +         [dict(kind='sheetpin', name=pin['name'], point=pin['point']) for pin in root_pins]
    derived = sw.connectivity({**{plan.key: plan.wiring for plan in plans}, '_root': root_wiring}, root_pins, root_labels)
    guard = sw.compare_with_model(derived, parts)
    if not guard['identical']:
        spec.design_dir.mkdir(parents=True, exist_ok=True)
        report = spec.design_dir / 'connectivity_guard_failure.json'
        report.write_text(json.dumps(guard, indent=2, default=str), encoding='utf-8')
        raise ValueError(f'connectivity guard: drawn geometry does not reproduce the model (report {report}): ' + json.dumps(
            {k: guard[k] for k in ('mismatch_count', 'unnamed', 'multi_named', 'dangling', 'problems')}, default=str)[:1500])
    # emit sheets
    label_size = num(presentation['label_size'])
    for number, plan in enumerate(plans, 2):
        sheet = gen.new_sheet(plan.key, plan.key, plan.title, '')
        sch = sheet['sch']
        sch.items.clear()
        sch.paper = plan.paper
        for text in plan.texts:
            if text['kind'] == 'title':
                sch.text(text['text'], text['x'], text['y'], presentation['title_size'], bold=True, justify='top')
            elif text['kind'] == 'note' and text['text']:
                sch.text(text['text'], text['x'], text['y'], presentation['note_size'])
            elif text['kind'] == 'heading':
                sch.text(text['text'], text['x'], text['y'], presentation['heading_size'], bold=True, justify='left bottom')
        for placed in plan.placed:
            if placed.kind == 'part':
                part = placed.part
                lib_id = gen.symbols[part['ref']]['lib_id']
                in_bom = bool(part.get('in_bom', part['kind'] not in ('TP', 'H')))
                props = {k: v for k, v in placed.texts.items() if v}
                sch.add_symbol(lib_id, placed.definition, part['ref'], part['value'], part['footprint'], placed.x, placed.y, placed.unit,
                               property_y=placed.property_y, in_bom=in_bom, on_board=bool(part.get('on_board', True)), angle=placed.angle, dnp=bool(part.get('dnp')),
                               properties_at=props or None)
                if placed.unit == 1:
                    gen.paths[part['ref']] = sheet['instance_path'] + '/' + sch.references[part['ref']]
                gen.placement.setdefault(part['ref'], []).append(dict(sheet=plan.key, page=part['page'], unit=placed.unit,
                                                                      x=placed.x, y=placed.y, angle=placed.angle))
            elif placed.kind == 'power':
                lib_id = f'{spec.library}:{placed.name}'
                gen.definitions[placed.name] = placed.definition
                sch.add_symbol(lib_id, placed.definition, placed.ref, placed.net, '', placed.x, placed.y, 1, in_bom=False, on_board=False,
                               angle=placed.angle, properties_at={k: v for k, v in placed.texts.items() if v} or None, hide_reference=True)
            else:  # PWR_FLAG
                gen.definitions[FLAG_SYMBOL] = FLAG_DEFINITION
                sch.add_symbol(f'{spec.library}:{FLAG_SYMBOL}', FLAG_DEFINITION, placed.ref, 'PWR_FLAG', '', placed.x, placed.y, 1,
                               in_bom=False, on_board=False, hide_reference=True, hide_value=True)
                gen.flags.append(dict(net=placed.net, reference=placed.ref, sheet=plan.key, x=placed.x, y=placed.y))
        for seg in plan.wiring.segments:
            sch.wire((num(seg.a[0]), num(seg.a[1])), (num(seg.b[0]), num(seg.b[1])))
        for j in plan.wiring.junctions:
            sch.junction((num(j[0]), num(j[1])))
        for label in plan.labels:
            point = (num(label['point'][0]), num(label['point'][1]))
            if label['kind'] == 'global':
                sch.global_label(label['name'], point, label.get('angle', 0), size=label_size)
            else:
                sch.hierarchical_label(label['name'], point, label.get('shape', 'bidirectional'), label.get('angle', 0), size=label_size)
        for p in plan.wiring.no_connects:
            sch.no_connect((num(p[0]), num(p[1])))
        sheet['page_number'] = number
    # root sheet: sheet symbols with pins, stubs and global anchors
    titles = Counter(s['title'] for s in gen.sheets)
    for sheet, entry, (sx, sy) in zip(gen.sheets, root_plan['entries'], root_plan['positions']):
        sheet_name = sheet['title'] if titles[sheet['title']] == 1 else f'{sheet["title"]} [{sheet["key"]}]'
        pin_lines = []
        for pin in [p for p in root_pins if p['sheet'] == sheet['key']]:
            angle = 180 if pin['side'] == 'left' else 0
            # KiCad draws a sheet pin's name inside the sheet: left edge = angle 180 + justify left, right edge = angle 0 +
            # justify right (every sheet pin of the KiCad 10 demo projects follows this; the inverse puts the text on the stub)
            pin_lines.append(f'(pin {quote(pin["name"])} {pin["shape"]} (at {num(pin["point"][0])} {num(pin["point"][1])} {angle}) '
                             f'(effects (font (size {label_size} {label_size})) (justify {"left" if angle == 180 else "right"})) '
                             f'(uuid "{uid(sheet["uuid"] + "/pin/" + pin["name"])}"))')
            root.wire((num(pin['point'][0]), num(pin['point'][1])), (num(pin['stub'][0]), num(pin['stub'][1])))
            root.global_label(pin['name'], (num(pin['stub'][0]), num(pin['stub'][1])), angle, size=label_size)
        root.items.append(f'''(sheet (at {num(sx)} {num(sy)}) (size {num(entry['w'])} {num(entry['h'])}) (stroke (width 0.254) (type default))
            (fill (color 0 0 0 0)) (uuid "{sheet['uuid']}")
            (property "Sheetname" {quote(sheet_name)} (at {num(sx)} {num(sy - 1.27)} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
            (property "Sheetfile" {quote(sheet['file'])} (at {num(sx)} {num(sy + entry['h'] + 1.27)} 0) (effects (font (size 1.0 1.0)) (justify left top)))
            {chr(10).join(pin_lines)}
            (instances (project {quote(spec.name)} (path "/{root.root_uuid}" (page "{sheet['page_number']}")))))''')
    summary = dict(style='wired', schema_version=2,
                   nets={net: dict(role=info['role'], pages=info['pages'], down=info['down']) for net, info in planner.nets.items()},
                   groups=planner.groups_by_page,
                   sheets=[dict(key=plan.key, paper=plan.paper, counts=plan.counts, ports=sorted(plan.ports)) for plan in plans],
                   exceptions=planner.exceptions, guard=dict(identical=True, pads_checked=guard['pads_checked']),
                   root=dict(paper=root_plan['paper'], sheet_pins=len(root_pins), global_anchors=len(root_labels)),
                   name_tags=sum(1 for plan in plans for l in plan.labels if l['kind'] == 'global'),
                   label_size=presentation['label_size'],
                   no_connects=guard['no_connects'])
    return _write_project_files(spec, gen, root, dict(gen.definitions), library, dict(presentation=summary), fallbacks, skipped,
                                diagnostics, flag_nets)

def demo_spec(kicad_dir: Path, design_dir: Path) -> dict:
    """Small self-contained project exercising every symbol path.

    A four-pin Kelvin-source FET (generated glyph), a three-pin FET (official Q_NMOS_GDS), a
    SOIC-16 driver with mixed pin types and no-connects, capacitors, resistors, 2x05 and 1x02
    connectors and PWR_FLAGs. Its fp-lib-table points at the stock footprint libraries only so
    ERC footprint links resolve; a real design gets its footprint libraries from the footprint module.
    """
    def pin_defs(text):
        return {n: dict(name=name, type=kind) for n, name, kind in (s.split(':') for s in text.split())}
    two = pin_defs('1:1:passive 2:2:passive')
    parts = [
        dict(ref='Q1', value='C3M0021120K', footprint='Package_TO_SOT_THT:TO-247-4_Vertical', kind='Q', page='01_power',
             nets={'1': 'G_H', '2': 'VBUS', '3': 'SW', '4': 'KS_H'}, pins=pin_defs('1:G:input 2:D:passive 3:S:passive 4:KS:passive'),
             mpn='C3M0021120K', maker='Wolfspeed', source='', note='Kelvin source package'),
        dict(ref='Q2', value='C3M0021120D', footprint='Package_TO_SOT_THT:TO-247-3_Vertical', kind='Q', page='01_power',
             nets={'1': 'G_L', '2': 'SW', '3': 'GND'}, pins=pin_defs('1:G:input 2:D:passive 3:S:passive'),
             mpn='C3M0021120D', maker='Wolfspeed', source='', note=''),
        dict(ref='J2', value='DC link', footprint='Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical', kind='J', page='01_power',
             nets={'1': 'VBUS', '2': 'GND'}, pins=pin_defs('1:VBUS:passive 2:GND:passive'), mpn='', maker='', source='', note=''),
        dict(ref='U1', value='UCC21520DW', footprint='Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm', kind='IC', page='02_driver',
             nets={'1': 'PWM_H', '2': 'PWM_L', '3': '3V3', '4': 'GND', '5': 'DISABLE', '6': 'DT', '7': None, '8': '3V3',
                   '9': 'KS_H', '10': 'GATE_H', '11': 'VDRV_H', '12': None, '13': None, '14': 'GND', '15': 'GATE_L', '16': 'VDRV_L'},
             pins=pin_defs('1:INA:input 2:INB:input 3:VCCI:power_in 4:GND:power_in 5:DIS:input 6:DT:passive 7:NC:no_connect '
                           '8:VCCI:power_in 9:VSSB:passive 10:OUTB:output 11:VDDB:power_in 12:NC:no_connect 13:NC:no_connect '
                           '14:VSSA:power_in 15:OUTA:output 16:VDDA:power_in'),
             mpn='UCC21520DW', maker='Texas Instruments', source='', note='Isolated dual gate driver'),
        dict(ref='R1', value='10', footprint='Resistor_SMD:R_0805_2012Metric', kind='R', page='02_driver',
             nets={'1': 'GATE_H', '2': 'G_H'}, pins=two, mpn='', maker='', source='', note=''),
        dict(ref='R2', value='10', footprint='Resistor_SMD:R_0805_2012Metric', kind='R', page='02_driver',
             nets={'1': 'GATE_L', '2': 'G_L'}, pins=two, mpn='', maker='', source='', note=''),
        dict(ref='C1', value='1u/50V', footprint='Capacitor_SMD:C_1210_3225Metric', kind='C', page='02_driver',
             nets={'1': 'VDRV_H', '2': 'KS_H'}, pins=two, mpn='', maker='', source='', note=''),
        dict(ref='C2', value='100n/50V', footprint='Capacitor_SMD:C_0805_2012Metric', kind='C', page='02_driver',
             nets={'1': '3V3', '2': 'GND'}, pins=two, mpn='', maker='', source='', note=''),
        dict(ref='J1', value='CTRL', footprint='Connector_PinHeader_2.54mm:PinHeader_2x05_P2.54mm_Vertical', kind='J', page='02_driver',
             nets={'1': 'PWM_H', '2': 'GND', '3': 'PWM_L', '4': 'GND', '5': 'DISABLE', '6': 'GND', '7': '3V3', '8': 'GND', '9': 'DT', '10': None},
             pins={str(n): dict(name=str(n), type='passive') for n in range(1, 11)}, mpn='', maker='', source='', note=''),
    ]
    libraries = sorted({p['footprint'].split(':')[0] for p in parts})
    return dict(name='AIPE_Demo', title='project_schematic demo - half bridge with isolated driver', revision='demo',
                comment='AUTOMATION SAMPLE ONLY - NOT A CONVERTER DESIGN', kicad_dir=kicad_dir, design_dir=design_dir,
                pages={'01_power': 'Half bridge', '02_driver': 'Gate driver, bypass and control connector'}, parts=parts,
                flag_nets=['VBUS', 'GND', '3V3', 'VDRV_H', 'VDRV_L'], flag_page='02_driver',
                header_lines=['Sample generated by automation.kicad_tools.project_schematic.',
                              'Exercises generated and official symbols, no-connects, PWR_FLAGs and project settings.'],
                page_notes={'01_power': 'Q1 uses a generated four-pin Kelvin-source symbol; Q2 the official Q_NMOS_GDS symbol.'},
                net_classes=[dict(name='HV', clearance=3.0, track_width=2.0, via_diameter=1.2, via_drill=0.6, nets=['VBUS', 'SW']),
                             dict(name='GATE', clearance=0.2, track_width=0.5, via_diameter=0.8, via_drill=0.4, nets=['GATE_*', 'G_*', 'KS_H'])],
                design_rules={'min_clearance': 0.2, 'min_track_width': 0.2, 'min_via_diameter': 0.6, 'min_through_hole_diameter': 0.3},
                dru_text='(rule "HV to other" (condition "A.NetClass == \'HV\' && B.NetClass != \'HV\'") (constraint clearance (min 3.0mm)))',
                fp_lib_table={lib: '${KICAD10_FOOTPRINT_DIR}/' + lib + '.pretty' for lib in libraries})


def main() -> None:
    """CLI: generate the demo project into a directory and optionally run native ERC on it."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--demo', type=Path, required=True, help='directory receiving kicad/ and design/')
    parser.add_argument('--erc', type=Path, help='run kicad-cli ERC and store the evidence under this directory')
    args = parser.parse_args()
    result = generate_project(demo_spec(args.demo / 'kicad', args.demo / 'design'))
    keys = ('root', 'mapping', 'parts_placed', 'continuation_sheets', 'symbol_fallbacks', 'diagnostics')
    print(json.dumps({k: result[k] for k in keys}, indent=2))
    if args.erc:
        from automation.kicad_tools.run_check import run_check
        code, manifest = run_check('erc', Path(result['root']), args.erc)
        print(manifest)
        raise SystemExit(code)


if __name__ == '__main__':
    main()
