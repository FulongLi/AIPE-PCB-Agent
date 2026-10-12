"""Map kicad-cli DRC JSON findings to board items (run under KiCad Python).

usage: python drc_diag.py BOARD.kicad_pcb drc.json [--limit N]
Groups violations by type and rule, resolves every item uuid to (kind, ref/pad or zone, net, layer) and prints positions.
"""
import collections
import json
import re
import sys

import pcbnew

board_path, drc_path = sys.argv[1], sys.argv[2]
limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 12
board = pcbnew.LoadBoard(board_path)
data = json.load(open(drc_path, encoding='utf-8-sig'))
mm = pcbnew.ToMM

BY_UUID = {}


def _index(item):
    try:
        BY_UUID[item.m_Uuid.AsString()] = item
    except Exception:  # noqa: BLE001
        pass


for _fp in board.GetFootprints():
    _index(_fp)
    for _pad in _fp.Pads():
        _index(_pad)
    for _g in _fp.GraphicalItems():
        _index(_g)
    _index(_fp.Reference())
    _index(_fp.Value())
for _t in board.GetTracks():
    _index(_t)
for _z in board.Zones():
    _index(_z)
for _d in board.GetDrawings():
    _index(_d)


def describe(uuid):
    item = BY_UUID.get(uuid)
    if item is None:
        return f'<not found {uuid}>'
    try:
        item = item.Cast()
    except Exception:  # noqa: BLE001
        pass
    cls = item.GetClass() if hasattr(item, 'GetClass') else type(item).__name__
    if isinstance(item, pcbnew.PAD):
        fp = item.GetParentFootprint()
        ref = fp.GetReference() if fp else '?'
        layers = 'THT' if item.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) else ('B' if fp and fp.IsFlipped() else 'F')
        return (f"PAD {ref}.{item.GetNumber()} [{item.GetNetname() or '-'}] {layers} @({mm(item.GetPosition().x):.3f},{mm(item.GetPosition().y):.3f}) "
                f"size {mm(item.GetSize().x):.2f}x{mm(item.GetSize().y):.2f}")
    if isinstance(item, pcbnew.PCB_VIA):
        return (f"VIA [{item.GetNetname()}] @({mm(item.GetPosition().x):.3f},{mm(item.GetPosition().y):.3f}) "
                f"d={mm(item.GetWidth(pcbnew.F_Cu)):.2f} drill={mm(item.GetDrillValue()):.2f}")
    if isinstance(item, pcbnew.PCB_TRACK):
        return (f"TRACK [{item.GetNetname()}] {board.GetLayerName(item.GetLayer())} ({mm(item.GetStart().x):.3f},{mm(item.GetStart().y):.3f})-"
                f"({mm(item.GetEnd().x):.3f},{mm(item.GetEnd().y):.3f}) w={mm(item.GetWidth()):.2f}")
    if isinstance(item, pcbnew.ZONE):
        bb = item.GetBoundingBox()
        kind = 'RULE_AREA' if item.GetIsRuleArea() else 'ZONE'
        layers = ','.join(board.GetLayerName(l) for l in item.GetLayerSet().Seq())
        return (f"{kind} {item.GetZoneName() or ''} [{item.GetNetname() or '-'}] {layers} prio={item.GetAssignedPriority()} "
                f"bbox=({mm(bb.GetX()):.1f},{mm(bb.GetY()):.1f})-({mm(bb.GetRight()):.1f},{mm(bb.GetBottom()):.1f})")
    if isinstance(item, pcbnew.PCB_SHAPE):
        bb = item.GetBoundingBox()
        fp = item.GetParentFootprint()
        owner = f" of {fp.GetReference()}" if fp else ''
        return (f"SHAPE{owner} {board.GetLayerName(item.GetLayer())} {item.ShowShape()} "
                f"bbox=({mm(bb.GetX()):.2f},{mm(bb.GetY()):.2f})-({mm(bb.GetRight()):.2f},{mm(bb.GetBottom()):.2f})")
    if isinstance(item, pcbnew.FOOTPRINT):
        return f"FOOTPRINT {item.GetReference()} @({mm(item.GetPosition().x):.2f},{mm(item.GetPosition().y):.2f})"
    if isinstance(item, pcbnew.PCB_TEXT):
        fp = item.GetParentFootprint()
        return f"TEXT{(' of ' + fp.GetReference()) if fp else ''} {board.GetLayerName(item.GetLayer())} {item.GetText()[:40]!r}"
    return f"{cls}"


groups = collections.defaultdict(list)
for v in data.get('violations', []):
    rule = re.search(r"\(.*?'([^']+)'", v.get('description', ''))
    groups[(v['type'], rule.group(1) if rule else '')].append(v)
print(f"violations {len(data.get('violations', []))}, unconnected {len(data.get('unconnected_items', []))}, parity {len(data.get('schematic_parity', []))}")
for (kind, rule), items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    print(f"\n=== {kind} / {rule or '-'}: {len(items)} ({items[0].get('severity')}) ===")
    for v in items[:limit]:
        nums = re.findall(r'(\d+\.\d+) mm', v.get('description', ''))
        print(f"  - need/actual {nums} @ {v['items'][0].get('pos') if v.get('items') else None}")
        for it in v.get('items', []):
            print(f"      {describe(it.get('uuid'))}")
    if len(items) > limit:
        print(f"  ... {len(items) - limit} more")
unc = data.get('unconnected_items', [])
if unc:
    nets = collections.Counter()
    print(f"\n=== unconnected ({len(unc)}) ===")
    for v in unc:
        m = re.search(r'\[([^\]]+)\]', ''.join(i.get('description', '') for i in v.get('items', [])))
        nets[m.group(1) if m else '?'] += 1
    print('  ' + ', '.join(f"{net}:{n}" for net, n in nets.most_common()))
    show_nets = set(sys.argv[sys.argv.index('--unconnected-nets') + 1].split(',')) if '--unconnected-nets' in sys.argv else None
    shown = 0
    for v in unc:
        text = ' | '.join(describe(i.get('uuid')) for i in v.get('items', []))
        if show_nets is None or any(f'[{n}]' in text for n in show_nets):
            print('  -', text)
            shown += 1
            if shown >= (limit if show_nets is None else 200):
                break
par = data.get('schematic_parity', [])
if par:
    print(f"\n=== schematic parity ({len(par)}) ===")
    for v in par[:limit]:
        print('  -', v.get('type'), v.get('description', '')[:160])
