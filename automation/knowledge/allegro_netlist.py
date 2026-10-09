"""Parse a Cadence/OrCAD ``pstxnet.dat`` expanded netlist (standard library only).

OrCAD Capture exports this text netlist for Allegro. It records each net, its
nodes (``REFDES PIN``) and optional net properties such as
``NET_SPACING_TYPE`` (the net class used for clearance rules). The parser is
used to check connectivity claims made in knowledge records against the
manufacturer's own netlist instead of a reading of the schematic drawing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

NODE = re.compile(r"^NODE_NAME\s+(\S+)\s+(\S+)")
PROPERTY = re.compile(r"^\s*([A-Z_]+)='([^']*)'")


@dataclass
class Net:
    name: str
    nodes: set = field(default_factory=set)
    properties: dict = field(default_factory=dict)


def parse(path: Path) -> dict[str, Net]:
    nets: dict[str, Net] = {}
    current: Net | None = None
    expect_name = False
    for line in path.read_text(encoding="latin-1").splitlines():
        if line.startswith("NET_NAME"):
            expect_name = True
            continue
        if expect_name:
            current = Net(line.strip().strip("'"))
            nets[current.name] = current
            expect_name = False
            continue
        if current is None:
            continue
        node = NODE.match(line)
        if node:
            current.nodes.add((node.group(1), node.group(2)))
            continue
        prop = PROPERTY.match(line)
        if prop and prop.group(1) != "C_SIGNAL":
            current.properties[prop.group(1)] = prop.group(2)
    return nets


def net_of(nets: dict[str, Net], refdes: str, pin: str) -> Net | None:
    for net in nets.values():
        if (refdes, pin) in net.nodes:
            return net
    return None


def connected(nets: dict[str, Net], a: tuple[str, str], b: tuple[str, str]) -> bool:
    net = net_of(nets, *a)
    return bool(net and b in net.nodes)


def spacing_classes(nets: dict[str, Net]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for net in nets.values():
        key = net.properties.get("NET_SPACING_TYPE", "(none)")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))
