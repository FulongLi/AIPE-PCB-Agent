"""Small deterministic KiCad schematic writer using installed library symbols."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path


def uid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "https://github.com/FulongLi/AIPE-PCB-Agent/" + name))


def quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def extract_symbol(library: Path, name: str) -> str:
    text = library.read_text(encoding="utf-8-sig")
    start = re.search(r'^\s*\(symbol ' + re.escape(quote(name)) + r'\s', text, re.MULTILINE)
    if not start:
        raise ValueError(f"Symbol {name!r} not found in {library}")
    offset = text.index("(", start.start())
    depth, quoted, escaped = 0, False, False
    for index in range(offset, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[offset:index + 1]
    raise ValueError(f"Unbalanced library symbol {name!r}")


def parse(text: str) -> list:
    """Parse a selected s-expression for inspection, preserving strings as values."""
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
    stack, result = [], []
    for token in tokens:
        if token == "(":
            node = []
            if stack:
                stack[-1].append(node)
            else:
                result.append(node)
            stack.append(node)
        elif token == ")":
            if not stack:
                raise ValueError("Unexpected closing parenthesis")
            stack.pop()
        else:
            if not stack:
                raise ValueError("Atom outside s-expression")
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    if stack or len(result) != 1:
        raise ValueError("Expected one balanced s-expression")
    return result[0]


def children(node: list, key: str) -> list[list]:
    return [value for value in node if isinstance(value, list) and value and value[0] == key]


def pins(symbol: str, unit: int = 1) -> list[dict]:
    result = []
    tree = parse(symbol)
    for body in children(tree, "symbol"):
        if not re.search(rf'_(0|{unit})_1$', body[1]):
            continue
        for pin in children(body, "pin"):
            at = children(pin, "at")[0]
            length = children(pin, "length")
            result.append({"number": children(pin, "number")[0][1],
                           "name": children(pin, "name")[0][1],
                           "type": pin[1], "x": float(at[1]), "y": float(at[2]),
                           "angle": float(at[3]), "length": float(length[0][1]) if length else 0.0})
    return result


ROTATIONS = (0, 90, 180, 270)
# Outward (away from the body) unit direction of a library pin by its own angle, in sheet coordinates
# (y down) for an unrotated symbol: a pin at angle 0 extends to the right into the body, so it leaves the body to the left.
PIN_OUTWARD = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}


def transform(px: float, py: float, angle: int = 0, mirror: str | None = None) -> tuple[float, float]:
    """Sheet-local offset of a library point for a symbol placed at `angle` with optional mirror.

    Library coordinates have y up, the sheet has y down.  Measured natively (KiCad 10.0.7, probe P1 of the
    V2.1 design notes) for 90 degrees and verified for every angle by the native fixture test:
    0: (x+px, y-py)   90: (x-py, y-px)   180: (x-px, y+py)   270: (x+py, y+px).
    `mirror` 'x' negates the library y, 'y' negates the library x, before the rotation.
    """
    if mirror == 'x':
        py = -py
    elif mirror == 'y':
        px = -px
    elif mirror:
        raise ValueError(f'mirror must be x, y or None, got {mirror!r}')
    angle = int(angle) % 360
    if angle == 0:
        return (px, -py)
    if angle == 90:
        return (-py, -px)
    if angle == 180:
        return (-px, py)
    if angle == 270:
        return (py, px)
    raise ValueError(f'angle must be one of {ROTATIONS}, got {angle!r}')


def rotate_direction(direction: tuple, angle: int = 0, mirror: str | None = None) -> tuple[int, int]:
    """Apply the symbol transform to a sheet-local unit direction (dx, dy)."""
    dx, dy = direction
    rx, ry = transform(dx, -dy, angle, mirror)  # a sheet-local vector is the library vector (dx, -dy)
    return (int(round(rx)), int(round(ry)))


def placed_pins(definition: str, unit: int, x: float, y: float, angle: int = 0, mirror: str | None = None) -> dict:
    """{pin number: dict(point=(x, y), outward=(dx, dy), type, name)} for a symbol placed at (x, y, angle)."""
    result = {}
    for p in pins(definition, unit):
        ox, oy = transform(p['x'], p['y'], angle, mirror)
        outward = rotate_direction(PIN_OUTWARD[int(p['angle']) % 360], angle, mirror)
        result[p['number']] = dict(point=(round(x + ox, 4), round(y + oy, 4)), outward=outward, type=p['type'], name=p['name'])
    return result


def power_symbol_definition(name: str, net: str, *, down: bool = False) -> str:
    """Project-library power symbol whose power_in pin at the origin names its net through the Value field.

    `down` draws the ground style (bars below the connection point); otherwise a rail bar above it.  The
    Value is visible so every rail and ground domain is labelled on the sheet (reference style rule B7).
    """
    if down:
        body = ('(polyline (pts (xy 0 0) (xy 0 -0.889)) (stroke (width 0) (type default)) (fill (type none)))'
                ' (polyline (pts (xy -1.27 -0.889) (xy 1.27 -0.889)) (stroke (width 0) (type default)) (fill (type none)))'
                ' (polyline (pts (xy -0.762 -1.397) (xy 0.762 -1.397)) (stroke (width 0) (type default)) (fill (type none)))'
                ' (polyline (pts (xy -0.254 -1.905) (xy 0.254 -1.905)) (stroke (width 0) (type default)) (fill (type none)))')
        value_at = '(at 0 -3.302 0)'
    else:
        body = ('(polyline (pts (xy 0 0) (xy 0 1.905)) (stroke (width 0) (type default)) (fill (type none)))'
                ' (polyline (pts (xy -1.27 1.905) (xy 1.27 1.905)) (stroke (width 0.254) (type default)) (fill (type none)))')
        value_at = '(at 0 3.302 0)'
    return (f'(symbol {quote(name)} (power) (pin_numbers (hide yes)) (pin_names (offset 0) (hide yes)) (in_bom no) (on_board no)\n'
            f'  (property "Reference" "#PWR" (at 0 -1.27 0) (hide yes) (effects (font (size 1.27 1.27))))\n'
            f'  (property "Value" {quote(net)} {value_at} (effects (font (size 1.0 1.0))))\n'
            f'  (property "Footprint" "" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))\n'
            f'  (property "Datasheet" "" (at 0 0 0) (hide yes) (effects (font (size 1.27 1.27))))\n'
            f'  (symbol {quote(name + "_0_1")} {body})\n'
            f'  (symbol {quote(name + "_1_1")} (pin power_in line (at 0 0 90) (length 0) '
            f'(name "pwr" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))))')


class Schematic:
    def __init__(self, name: str, title: str, paper: str = "A4", *, project_name=None,
                 instance_path=None, revision="smoke", comment="AUTOMATION TEST ONLY - NOT A POWER CONVERTER"):
        self.name, self.title, self.paper = name, title, paper
        self.root_uuid = uid(name + "/root")
        self.project_name = project_name or name
        self.instance_path = instance_path or "/" + self.root_uuid
        self.revision, self.comment = revision, comment
        self.symbols: dict[str, str] = {}
        self.items: list[str] = []
        self.references: dict[str, str] = {}

    def add_symbol(self, lib_id: str, definition: str, reference: str, value: str,
                   footprint: str, x: float, y: float, unit: int = 1, *, property_y=None,
                   in_bom=True, on_board=True, angle: int = 0, mirror: str | None = None, dnp: bool = False,
                   properties_at: dict | None = None, hide_value: bool = False,
                   hide_reference: bool = False) -> dict[str, tuple]:
        """Place a symbol instance; returns {pin number: (x, y)} of its connection points.

        The legacy call (angle 0, no mirror, dnp False, no properties_at) writes exactly the V2 text.
        `properties_at` = {'Reference' | 'Value': (x, y, justify)} positions the visible texts explicitly
        (justify such as 'left' or 'left bottom'); `angle` / `mirror` follow transform().
        """
        self.symbols[lib_id] = definition.replace(
            '(symbol ' + quote(lib_id.split(":")[-1]), '(symbol ' + quote(lib_id), 1)
        symbol_uuid = uid(self.name + "/" + reference + (f"/unit{unit}" if unit != 1 else ""))
        self.references[reference] = symbol_uuid
        angle = int(angle) % 360
        if angle not in ROTATIONS:
            raise ValueError(f'angle must be one of {ROTATIONS}, got {angle!r}')
        properties = []
        for key, text, dy, hidden in (("Reference", reference, -6.35 if property_y is None else property_y, hide_reference),
                                      ("Value", value, 6.35 if property_y is None else property_y+2.54, hide_value),
                                      ("Footprint", footprint, 0, True),
                                      ("Datasheet", "", 0, True)):
            if properties_at and key in properties_at:
                px, py, justify, *rest = properties_at[key]
                size = rest[0] if rest else 1.27
                # KiCad draws a field at (field angle + symbol angle) and mirrors the justification at 180 degrees;
                # these values keep every field horizontal and justified as requested (measured, KiCad 10.0.7)
                field_angle = {0: 0, 90: 270, 180: 0, 270: 90}[int(angle) % 360]
                if int(angle) % 360 == 180 and justify:
                    justify = justify.replace('left', '\x00').replace('right', 'left').replace('\x00', 'right')
                effects = f'(effects (font (size {size} {size})) (justify {justify}))' if justify else f'(effects (font (size {size} {size})))'
                properties.append(f'(property {quote(key)} {quote(text)} (at {px} {py} {field_angle}) '
                                  f'{"(hide yes)" if hidden else ""} {effects})')
                continue
            properties.append(f'(property {quote(key)} {quote(text)} (at {x} {y + dy} 0) '
                              f'{"(hide yes)" if hidden else ""} '
                              '(effects (font (size 1.27 1.27))))')
        pin_info = pins(definition, unit)
        pin_lines = "\n".join(f'(pin {quote(p["number"])} (uuid "{uid(symbol_uuid + p["number"])}"))'
                              for p in pin_info)
        placement = f'(at {x} {y} {angle})' + (f' (mirror {mirror})' if mirror else '')
        self.items.append(f'''(symbol (lib_id {quote(lib_id)}) {placement}
          (unit {unit}) (in_bom {"yes" if in_bom else "no"}) (on_board {"yes" if on_board else "no"}) (dnp {"yes" if dnp else "no"}) (uuid "{symbol_uuid}")
          {chr(10).join(properties)}
          {pin_lines}
          (instances (project {quote(self.project_name)} (path {quote(self.instance_path)}
            (reference {quote(reference)}) (unit {unit})))))''')
        if angle == 0 and not mirror:
            return {p["number"]: (round(x + p["x"], 4), round(y - p["y"], 4)) for p in pin_info}
        return {n: info['point'] for n, info in placed_pins(definition, unit, x, y, angle, mirror).items()}

    def wire(self, start: tuple, end: tuple) -> None:
        self.items.append(f'''(wire (pts (xy {start[0]} {start[1]}) (xy {end[0]} {end[1]}))
          (stroke (width 0) (type default)) (uuid "{uid(self.name + '/wire/' + str(len(self.items)))}"))''')

    def label(self, name: str, point: tuple) -> None:
        self.items.append(f'''(label {quote(name)} (at {point[0]} {point[1]} 0)
          (effects (font (size 1.27 1.27)) (justify left bottom))
          (uuid "{uid(self.name + '/label/' + str(len(self.items)))}"))''')

    def global_label(self, name: str, point: tuple, angle=0, *, shape: str = 'bidirectional', size: float = 1.0,
                     justify: str | None = None) -> None:
        if justify is None:
            justify = "left" if angle == 0 else "right"
        self.items.append(f'''(global_label {quote(name)} (shape {shape})
          (at {point[0]} {point[1]} {angle})
          (effects (font (size {size} {size})) (justify {justify}))
          (uuid "{uid(self.name + '/global/' + str(len(self.items)))}"))''')

    def hierarchical_label(self, name: str, point: tuple, shape: str = 'bidirectional', angle=0, *, size: float = 1.0) -> None:
        """Sheet port; `angle` 0 reads to the right of the point, 180 to the left (text stays horizontal)."""
        justify = "left" if angle in (0, 90) else "right"
        self.items.append(f'''(hierarchical_label {quote(name)} (shape {shape})
          (at {point[0]} {point[1]} {angle})
          (effects (font (size {size} {size})) (justify {justify}))
          (uuid "{uid(self.name + '/hier/' + str(len(self.items)))}"))''')

    def junction(self, point: tuple) -> None:
        self.items.append(f'(junction (at {point[0]} {point[1]}) (diameter 0) (color 0 0 0 0) '
                          f'(uuid "{uid(self.name + "/junction/" + str(len(self.items)))}"))')

    def rectangle(self, start: tuple, end: tuple, *, width: float = 0.254, line_type: str = 'dash',
                  fill: str | None = None) -> None:
        """Graphic rectangle (group frame or isolation tint); electrically inert."""
        fill_text = f'(fill (type color) (color {fill}))' if fill else '(fill (type none))'
        self.items.append(f'(rectangle (start {start[0]} {start[1]}) (end {end[0]} {end[1]}) '
                          f'(stroke (width {width}) (type {line_type})) {fill_text} '
                          f'(uuid "{uid(self.name + "/rect/" + str(len(self.items)))}"))')

    def no_connect(self, point: tuple) -> None:
        self.items.append(f'(no_connect (at {point[0]} {point[1]}) (uuid "{uid(self.name + "/nc/" + str(len(self.items)))}"))')

    def text(self, value: str, x: float, y: float, size=1.27, *, bold: bool = False, justify: str = 'left top') -> None:
        font = f'(font (size {size} {size})' + (' (bold yes)' if bold else '') + ')'
        self.items.append(f'''(text {quote(value)} (at {x} {y} 0)
          (effects {font} (justify {justify}))
          (uuid "{uid(self.name + '/text/' + str(len(self.items)))}"))''')

    def write(self, path: Path) -> None:
        text = f'''(kicad_sch (version 20250114) (generator "aipe")
          (uuid "{self.root_uuid}") (paper {quote(self.paper)})
          (title_block (title {quote(self.title)}) (rev {quote(self.revision)})
            (comment 1 {quote(self.comment)}))
          (lib_symbols {chr(10).join(self.symbols.values())})
          {chr(10).join(self.items)}
          (sheet_instances (path "/" (page "1")))
        )\n'''
        parse(text)
        path.write_text(text, encoding="utf-8")
