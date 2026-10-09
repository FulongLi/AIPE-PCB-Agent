"""Read component-pin connectivity from an ODB++ archive (standard library only).

Uses ``steps/<step>/eda/data`` (NET records with ``SNT TOP T|B <comp> <toeprint>``
subnets and PKG/PIN definitions) and the ``comp_+_top``/``comp_+_bot``
component layers (``CMP <pkg> x y rot mirror <refdes> <part>`` followed by
``TOP <toeprint> ...`` lines). The archive is read in memory; nothing is
extracted to disk, so archive member paths are never trusted as file paths.
"""
from __future__ import annotations

import tarfile
from pathlib import Path


def _members(archive: Path, step: str) -> dict[str, str]:
    wanted = {f"steps/{step}/eda/data": "eda",
              f"steps/{step}/layers/comp_+_top/components": "T",
              f"steps/{step}/layers/comp_+_bot/components": "B"}
    found: dict[str, str] = {}
    with tarfile.open(archive, "r:*") as bundle:
        for member in bundle.getmembers():
            for suffix, key in wanted.items():
                if member.isfile() and member.name.endswith(suffix):
                    found[key] = bundle.extractfile(member).read().decode("latin-1")
    return found


def _components(text: str) -> list[tuple[int, str]]:
    """Return (package index, refdes) for each CMP record in file order."""
    result = []
    for line in text.splitlines():
        if line.startswith("CMP "):
            parts = line.split()
            result.append((int(parts[1]), parts[6]))
    return result


def connectivity(archive: Path, step: str = "pcb") -> dict[str, set[tuple[str, str]]]:
    """Map net name -> {(refdes, pin name)} for every component pin in the step."""
    files = _members(archive, step)
    packages: list[list[str]] = []
    nets: dict[str, set[tuple[str, str]]] = {}
    current = None
    for line in files["eda"].splitlines():
        if line.startswith("NET "):
            current = line.split(maxsplit=1)[1].strip()
            nets[current] = set()
        elif line.startswith("PKG "):
            packages.append([])
        elif line.startswith("PIN ") and packages:
            packages[-1].append(line.split()[1])
    sides = {side: _components(files.get(side, "")) for side in ("T", "B")}
    current = None
    for line in files["eda"].splitlines():
        if line.startswith("NET "):
            current = line.split(maxsplit=1)[1].strip()
        elif line.startswith("PKG "):
            current = None
        elif line.startswith("SNT TOP ") and current is not None:
            _, _, side, comp, toeprint = line.split()[:5]
            package, refdes = sides[side][int(comp)]
            pin = packages[package][int(toeprint)]
            nets[current].add((refdes, pin))
    return nets


def nets_of(nets: dict[str, set[tuple[str, str]]], refdes: str) -> dict[str, str]:
    """Pin name -> net name for one component."""
    return {pin: name for name, nodes in nets.items() for ref, pin in nodes if ref == refdes}
