"""Export checked KiCad source into a fresh directory with command/hash evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from automation.setup.detect_kicad import find_kicad_cli


def export(source: Path, output: Path, layers: str) -> None:
    cli = find_kicad_cli()
    if not cli:
        raise FileNotFoundError("KiCad CLI unavailable")
    board = source.with_suffix(".kicad_pcb").resolve(strict=True)
    schematic = source.with_suffix(".kicad_sch").resolve(strict=True)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    for name in ("review", "gerber", "drill", "bom", "pick_and_place", "step", "logs"):
        (output / name).mkdir()
    commands = [
        ("schematic_pdf", ["sch", "export", "pdf", "-o", str(output / "review/schematic.pdf"), str(schematic)]),
        ("pcb_pdf", ["pcb", "export", "pdf", "--mode-multipage", "--layers",
                     ",".join(layer for layer in layers.split(",") if layer != "Edge.Cuts"),
                     "--common-layers", "Edge.Cuts", "--scale", "0",
                     "-o", str(output / "review/pcb_layout.pdf"), str(board)]),
        ("gerber", ["pcb", "export", "gerbers", "--layers", layers + ",F.Paste,B.Paste,F.Mask,B.Mask",
                    "-o", str(output / "gerber") + os.sep, str(board)]),
        ("drill", ["pcb", "export", "drill", "--format", "excellon", "--generate-report",
                   "--report-path", str(output / "drill/drill-report.rpt"),
                   "-o", str(output / "drill") + os.sep, str(board)]),
        ("bom", ["sch", "export", "bom", "-o", str(output / "bom/bom.csv"), str(schematic)]),
        ("placement", ["pcb", "export", "pos", "--format", "csv", "--units", "mm",
                       "--side", "both", "-o", str(output / "pick_and_place/positions.csv"), str(board)]),
        ("step", ["pcb", "export", "step", "--subst-models", "--include-tracks", "--include-zones",
                  "-o", str(output / "step/board.step"), str(board)]),
        ("front", ["pcb", "render", "--side", "top", "--width", "1200", "--height", "900",
                   "-o", str(output / "review/pcb_front.png"), str(board)]),
        ("back", ["pcb", "render", "--side", "bottom", "--width", "1200", "--height", "900",
                  "-o", str(output / "review/pcb_back.png"), str(board)]),
        ("isometric", ["pcb", "render", "--side", "top", "--rotate", "330,0,25", "--width", "1200",
                       "--height", "900", "-o", str(output / "review/pcb_3d.png"), str(board)]),
        ("netlist", ["sch", "export", "netlist", "--format", "kicadxml",
                     "-o", str(output / "netlist.xml"), str(schematic)]),
    ]
    evidence = {"status": "in_progress", "commands": [], "artifacts": {}}
    try:
        for name, arguments in commands:
            command = [str(cli), *arguments]
            completed = subprocess.run(command, capture_output=True, text=True,
                                       encoding="utf-8", errors="replace", timeout=300)
            (output / "logs" / f"{name}.log").write_text(
                completed.stdout + completed.stderr, encoding="utf-8")
            evidence["commands"].append({"name": name, "command": command, "exit_code": completed.returncode})
            print(f"{name}: exit {completed.returncode}", flush=True)
            if completed.returncode:
                raise RuntimeError(f"Export {name} failed; see {output / 'logs'}")
        for folder in ("review", "gerber", "drill", "bom", "pick_and_place", "step"):
            if not any(p.is_file() and p.stat().st_size for p in (output / folder).iterdir()):
                raise RuntimeError(f"Export directory {folder} has no nonempty files")
        for path in output.rglob("*"):
            if path.is_file():
                evidence["artifacts"][path.relative_to(output).as_posix()] = {
                    "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
        evidence["status"] = "passed"
    except Exception as exc:
        evidence["status"] = "failed"
        evidence["error"] = str(exc)
        raise
    finally:
        (output / "export-manifest.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="KiCad project basename or source path")
    parser.add_argument("--output", type=Path, required=True, help="Must not already exist")
    parser.add_argument("--layers", default="F.Cu,B.Cu,F.SilkS,B.SilkS,Edge.Cuts")
    args = parser.parse_args()
    export(args.source, args.output, args.layers)
