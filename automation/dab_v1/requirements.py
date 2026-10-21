"""Requirement files of the AIPE 10 kW DAB (DAB-V1): paths, YAML loading and validation.

Every generator of ``automation.dab_v1`` takes its numbers from ``examples/dab-10kw/requirements/*.yaml``; nothing
about a board (size, stack-up, devices, clearances, pin maps, placement regions, routing parameters) is written in
code.  YAML is read with PyYAML when it is importable and otherwise with the small subset parser below, because
KiCad's bundled Python (which runs the board stages) ships without PyYAML.  The subset is what the requirement
files use: block mappings and sequences, flow collections ``[...]`` / ``{...}`` (nested), quoted and plain scalars,
``null``/``true``/``false``, integers and floats, comments.  A unit test checks that both loaders agree on every
requirement file of the repository, so the fallback cannot drift silently.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / 'examples/dab-10kw'
REQUIREMENTS = EXAMPLE / 'requirements'
DESIGN = EXAMPLE / 'design'
VERIFICATION = EXAMPLE / 'verification'
MANUFACTURING = EXAMPLE / 'manufacturing'
BOARDS = ('primary-power', 'secondary-power', 'control')
GENERATION = 'DAB-V1'
BANNER = f'AI-GENERATED ENGINEERING PROTOTYPE - {GENERATION} - HUMAN REVIEW REQUIRED - NOT HARDWARE QUALIFIED'

_SCALAR_INT = re.compile(r'^[-+]?\d+$')
_SCALAR_FLOAT = re.compile(r'^[-+]?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?$')


class YamlError(ValueError):
    pass


def _scalar(text: str):
    """Plain-scalar conversion of the subset (PyYAML-compatible for the values the requirement files use)."""
    t = text.strip()
    if t == '' or t in ('null', '~'):
        return None
    if t == 'true':
        return True
    if t == 'false':
        return False
    if len(t) >= 2 and t[0] == t[-1] and t[0] in '\'"':
        inner = t[1:-1]
        return inner.replace("''", "'") if t[0] == "'" else bytes(inner, 'utf-8').decode('unicode_escape')
    if _SCALAR_INT.match(t):
        return int(t)
    if _SCALAR_FLOAT.match(t) and any(ch in t for ch in '.eE') and not t.lower().startswith(('0x', '0o')):
        # PyYAML 1.1 needs a dot for a float ("1e3" stays a string); mirror that
        if '.' in t:
            return float(t)
        return t
    return t


def _strip_comment(line: str) -> str:
    """Remove a trailing comment that is outside quotes ('#' preceded by whitespace or at column 0)."""
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in '\'"':
            quote = ch
        elif ch == '#' and (i == 0 or line[i - 1] in ' \t'):
            return line[:i].rstrip()
    return line.rstrip()


def _split_flow(text: str) -> list[str]:
    """Split a flow collection body on top-level commas."""
    parts, depth, quote, start = [], 0, None, 0
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = None
        elif ch in '\'"':
            quote = ch
        elif ch in '[{':
            depth += 1
        elif ch in ']}':
            depth -= 1
        elif ch == ',' and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    tail = text[start:]
    if tail.strip():
        parts.append(tail)
    return parts


def _flow_value(text: str):
    t = text.strip()
    if t.startswith('['):
        if not t.endswith(']'):
            raise YamlError(f'unterminated flow sequence: {text!r}')
        return [_flow_value(p) for p in _split_flow(t[1:-1])]
    if t.startswith('{'):
        if not t.endswith('}'):
            raise YamlError(f'unterminated flow mapping: {text!r}')
        result = {}
        for item in _split_flow(t[1:-1]):
            key, value = _split_key(item)
            result[_scalar(key)] = _flow_value(value)
        return result
    return _scalar(t)


def _split_key(item: str) -> tuple[str, str]:
    """Split 'key: value' at the first ': ' (or trailing ':') outside quotes."""
    quote = None
    for i, ch in enumerate(item):
        if quote:
            if ch == quote:
                quote = None
        elif ch in '\'"':
            quote = ch
        elif ch == ':' and (i + 1 == len(item) or item[i + 1] in ' \t'):
            return item[:i], item[i + 1:]
    raise YamlError(f'expected "key: value", got {item!r}')


def _parse_block(lines: list[tuple[int, str]], index: int, indent: int):
    """Parse the block starting at lines[index] whose items are indented by ``indent``; returns (value, next index)."""
    if index >= len(lines):
        return None, index
    first_indent, first = lines[index]
    if first_indent != indent:
        raise YamlError(f'bad indentation near: {first!r}')
    if first.startswith('- ') or first == '-':
        result = []
        while index < len(lines) and lines[index][0] == indent and (lines[index][1].startswith('- ') or lines[index][1] == '-'):
            body = lines[index][1][1:].strip()
            if not body:
                value, index = _parse_block(lines, index + 1, _next_indent(lines, index + 1, indent))
                result.append(value)
                continue
            if body.startswith(('[', '{')) or ':' not in body or _is_scalar_with_colon(body):
                result.append(_flow_value(body))
                index += 1
                continue
            # mapping inside a sequence item: re-indent its first line and parse the following deeper lines with it
            item_indent = indent + 2
            sub = [(item_indent, body)]
            index += 1
            while index < len(lines) and lines[index][0] > indent:
                sub.append(lines[index])
                index += 1
            value, _ = _parse_block(sub, 0, item_indent)
            result.append(value)
        return result, index
    result = {}
    while index < len(lines) and lines[index][0] == indent:
        text = lines[index][1]
        if text.startswith('- '):
            break
        key, value = _split_key(text)
        key = _scalar(key)
        if value.strip():
            result[key] = _flow_value(value)
            index += 1
        else:
            nxt = index + 1
            if nxt < len(lines) and lines[nxt][0] > indent:
                result[key], index = _parse_block(lines, nxt, lines[nxt][0])
            elif nxt < len(lines) and lines[nxt][0] == indent and lines[nxt][1].startswith('- '):
                result[key], index = _parse_block(lines, nxt, indent)  # sequence at the same indentation as its key
            else:
                result[key] = None
                index = nxt
    return result, index


def _is_scalar_with_colon(body: str) -> bool:
    """'https://x' or a quoted string is a scalar even though it contains ':'."""
    try:
        _split_key(body)
    except YamlError:
        return True
    return body[0] in '\'"'


def _next_indent(lines, index, parent):
    if index < len(lines) and lines[index][0] > parent:
        return lines[index][0]
    raise YamlError('empty sequence item')


def load_yaml_text(text: str):
    """Parse the YAML subset; raises YamlError on anything outside it."""
    lines = []
    for raw in text.splitlines():
        if raw.strip().startswith('#') or not raw.strip():
            continue
        stripped = _strip_comment(raw.expandtabs(2))
        if not stripped.strip():
            continue
        lines.append((len(stripped) - len(stripped.lstrip(' ')), stripped.strip()))
    if not lines:
        return None
    value, index = _parse_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise YamlError(f'unparsed content near: {lines[index][1]!r}')
    return value


def load_yaml(path: Path):
    """Load a requirement file with PyYAML when available, otherwise with the subset parser."""
    text = Path(path).read_text(encoding='utf-8-sig')
    try:
        import yaml  # type: ignore
    except ImportError:
        return load_yaml_text(text)
    return yaml.safe_load(text)


def requirement_files() -> dict:
    return {p.stem: p for p in sorted(REQUIREMENTS.glob('*.yaml'))}


class Requirements:
    """All requirement files of the example, validated once."""

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root else REQUIREMENTS
        self.specification = load_yaml(self.root / 'specification.yaml')
        self.constraints = load_yaml(self.root / 'design_constraints.yaml')
        self.components = load_yaml(self.root / 'components.yaml')
        self.interfaces = load_yaml(self.root / 'interfaces.yaml')
        self.floorplans = {b: load_yaml(self.root / f'floorplan_{b}.yaml') for b in BOARDS}
        self.routing = {b: load_yaml(self.root / f'routing_{b}.yaml') for b in BOARDS}
        self.validate()

    def board(self, board: str) -> dict:
        if board not in BOARDS:
            raise KeyError(f'unknown board {board!r}; choose from {BOARDS}')
        return self.constraints['boards'][board]

    def side(self, board: str) -> str:
        return self.board(board)['side']

    def validate(self) -> None:
        for name, data in (('specification', self.specification), ('design_constraints', self.constraints),
                           ('components', self.components), ('interfaces', self.interfaces)):
            if not isinstance(data, dict) or data.get('schema') != 1:
                raise ValueError(f'{name}.yaml must be a mapping with schema: 1')
        boards = self.constraints.get('boards', {})
        if set(boards) != set(BOARDS):
            raise ValueError(f'design_constraints boards must be exactly {BOARDS}, got {sorted(boards)}')
        for board, cfg in boards.items():
            for key in ('name', 'title', 'side', 'size_mm', 'layers', 'copper_um', 'thickness_mm', 'stackup',
                        'min_track_mm', 'min_clearance_mm', 'via_mm', 'min_hole_clearance_mm'):
                if key not in cfg:
                    raise ValueError(f'board {board} lacks {key}')
            if len(cfg['size_mm']) != 2 or min(cfg['size_mm']) <= 0:
                raise ValueError(f'board {board}: size_mm must be two positive numbers')
            copper = [row for row in cfg['stackup'] if row[1] == 'copper']
            if len(copper) != cfg['layers'] or len(cfg['copper_um']) != cfg['layers']:
                raise ValueError(f'board {board}: stackup copper layers must match layers and copper_um')
            total = sum(float(row[2]) for row in cfg['stackup'])
            if abs(total - float(cfg['thickness_mm'])) > 0.051:
                raise ValueError(f'board {board}: stackup totals {total:.3f} mm, thickness_mm says {cfg["thickness_mm"]}')
            if cfg['via_mm'][1] >= cfg['via_mm'][0]:
                raise ValueError(f'board {board}: via drill must be smaller than the via diameter')
        iso = self.constraints['insulation_reference']
        table = iso['functional_gap_mm_by_working_V']
        if any(b[0] <= a[0] or b[1] < a[1] for a, b in zip(table, table[1:])):
            raise ValueError('functional_gap_mm_by_working_V must increase in voltage and not decrease in spacing')
        if float(iso['reinforced_hv_to_selv_mm']) < table[-1][1]:
            raise ValueError('the reinforced HV-to-SELV spacing must not be below the largest functional spacing')
        pins = self.interfaces['control_harness']['pins']
        if sorted(int(k) for k in pins) != list(range(1, 41)):
            raise ValueError('control_harness.pins must define contacts 1..40 exactly once')
        card = self.interfaces['controlcard']['signals']
        if any(not 1 <= int(k) <= 180 for k in card):
            raise ValueError('controlcard.signals contacts must lie in 1..180')
        nets = [v for v in card.values() if v]
        duplicates = sorted({n for n in nets if nets.count(n) > 1 and n not in ('GND_CTRL', '5V0')})
        if duplicates:
            raise ValueError(f'controlcard.signals assigns a signal to several contacts: {duplicates}')
        for board in BOARDS:
            fp = self.floorplans[board]
            if not isinstance(fp, dict) or fp.get('board') != board:
                raise ValueError(f'floorplan_{board}.yaml must declare board: {board}')
            if list(fp['outline_mm']) != list(boards[board]['size_mm']):
                raise ValueError(f'floorplan_{board}.yaml outline differs from design_constraints size_mm')
            rp = self.routing[board]
            if not isinstance(rp, dict) or rp.get('board') != board:
                raise ValueError(f'routing_{board}.yaml must declare board: {board}')

    def functional_gap_mm(self, working_voltage: float) -> float:
        """Functional spacing (mm) for a working-voltage difference from the reference table (last row above)."""
        table = self.constraints['insulation_reference']['functional_gap_mm_by_working_V']
        if working_voltage <= table[0][0]:
            return float(table[0][1])
        for (v0, m0), (v1, m1) in zip(table, table[1:]):
            if working_voltage <= v1:
                mm = m0 + (m1 - m0) * (working_voltage - v0) / (v1 - v0)
                return math.ceil(mm * 20 - 1e-9) / 20  # linear interpolation, rounded up to 0.05 mm
        return float(table[-1][1])

    def reinforced_gap_mm(self) -> float:
        return float(self.constraints['insulation_reference']['reinforced_hv_to_selv_mm'])

    def dump(self, path: Path) -> None:
        """Write the resolved requirement set as JSON next to the design records (what the generators saw)."""
        payload = dict(specification=self.specification, design_constraints=self.constraints, components=self.components,
                       interfaces=self.interfaces, floorplans=self.floorplans, routing=self.routing)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, default=str) + '\n', encoding='utf-8')


def load() -> Requirements:
    return Requirements()
