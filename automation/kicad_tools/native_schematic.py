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
            result.append({"number": children(pin, "number")[0][1],
                           "name": children(pin, "name")[0][1],
                           "type": pin[1], "x": float(at[1]), "y": float(at[2]),
                           "angle": float(at[3])})
    return result


class Schematic:
    def __init__(self, name: str, title: str, paper: str = "A4"):
        self.name, self.title, self.paper = name, title, paper
        self.root_uuid = uid(name + "/root")
        self.symbols: dict[str, str] = {}
        self.items: list[str] = []
        self.references: dict[str, str] = {}

    def add_symbol(self, lib_id: str, definition: str, reference: str, value: str,
                   footprint: str, x: float, y: float, unit: int = 1) -> dict[str, tuple]:
        self.symbols[lib_id] = definition.replace(
            '(symbol ' + quote(lib_id.split(":")[-1]), '(symbol ' + quote(lib_id), 1)
        symbol_uuid = uid(self.name + "/" + reference)
        self.references[reference] = symbol_uuid
        properties = []
        for key, text, dy, hidden in (("Reference", reference, -6.35, False),
                                      ("Value", value, 6.35, False),
                                      ("Footprint", footprint, 0, True),
                                      ("Datasheet", "", 0, True)):
            properties.append(f'(property {quote(key)} {quote(text)} (at {x} {y + dy} 0) '
                              f'{"(hide yes)" if hidden else ""} '
                              '(effects (font (size 1.27 1.27))))')
        pin_info = pins(definition, unit)
        pin_lines = "\n".join(f'(pin {quote(p["number"])} (uuid "{uid(symbol_uuid + p["number"])}"))'
                              for p in pin_info)
        self.items.append(f'''(symbol (lib_id {quote(lib_id)}) (at {x} {y} 0)
          (unit {unit}) (in_bom yes) (on_board yes) (dnp no) (uuid "{symbol_uuid}")
          {chr(10).join(properties)}
          {pin_lines}
          (instances (project {quote(self.name)} (path "/{self.root_uuid}"
            (reference {quote(reference)}) (unit {unit})))))''')
        return {p["number"]: (x + p["x"], y - p["y"]) for p in pin_info}

    def wire(self, start: tuple, end: tuple) -> None:
        self.items.append(f'''(wire (pts (xy {start[0]} {start[1]}) (xy {end[0]} {end[1]}))
          (stroke (width 0) (type default)) (uuid "{uid(self.name + '/wire/' + str(len(self.items)))}"))''')

    def label(self, name: str, point: tuple) -> None:
        self.items.append(f'''(label {quote(name)} (at {point[0]} {point[1]} 0)
          (effects (font (size 1.27 1.27)) (justify left bottom))
          (uuid "{uid(self.name + '/label/' + str(len(self.items)))}"))''')

    def write(self, path: Path) -> None:
        text = f'''(kicad_sch (version 20250114) (generator "aipe")
          (uuid "{self.root_uuid}") (paper {quote(self.paper)})
          (title_block (title {quote(self.title)}) (rev "smoke")
            (comment 1 "AUTOMATION TEST ONLY - NOT A POWER CONVERTER"))
          (lib_symbols {chr(10).join(self.symbols.values())})
          {chr(10).join(self.items)}
          (sheet_instances (path "/" (page "1")))
        )\n'''
        parse(text)
        path.write_text(text, encoding="utf-8")
