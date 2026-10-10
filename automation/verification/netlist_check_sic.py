"""Independent pad/net equality check for the two V2 boards (the netlist step of verify_buck.py, per board).

Compares three pad -> net maps exactly and writes verification/netlist_check_<board>.json:

  model      design/circuit_<board>.json, the electrical source of truth written by
             automation/kicad_tools/sic_buck_<board>_model.py (pad -> net, null = no connection);
  schematic  the kicad-cli XML netlist exported from the board's root schematic
             (default manufacturing/<board_dir>/netlist.xml, i.e. the export bundle's copy);
  board      every footprint pad of kicad/<board_dir>/<name>.kicad_pcb read with pcbnew
             (nets named "unconnected-..." or empty count as no connection, as in verify_buck.py).

exact_match is true only when all three maps agree pad for pad and the component reference sets are
identical. A missing board file is recorded as status "board_missing" with exact_match false; nothing
is inferred from the schematic in its place. The check is CAD connectivity only - it qualifies no
electrical, thermal or EMI behaviour.

Run (pcbnew is needed when the board exists; the script re-executes itself under KiCad's Python):
    python automation/verification/netlist_check_sic.py --board control [--xml <netlist.xml>] [--pcb <board>]
                                                         [--output <netlist_check_<board>.json>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXAMPLE = ROOT / "examples/sic-buck-400v-200v-5kw"
BOARDS = {
    "power": dict(dir="power_board", name="AIPE_SiC_Buck_Power"),
    "control": dict(dir="control_board", name="AIPE_SiC_Buck_Control"),
}
UNNAMED_PREFIX = "unconnected-"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_model(path: Path) -> tuple[dict, set, dict]:
    parts = json.loads(path.read_text(encoding="utf-8-sig"))
    expected = {(p["ref"], str(pin)): net for p in parts for pin, net in p["nets"].items() if net}
    refs = {p["ref"] for p in parts}
    info = {"parts": len(parts), "dnp_parts": sum(1 for p in parts if p.get("dnp")),
            "mapped_pins": len(expected), "named_nets": len(set(expected.values()))}
    return expected, refs, info


def load_xml(path: Path) -> tuple[dict, set, dict, list]:
    tree = ET.parse(path).getroot()
    nodes: dict = {}
    duplicates = []
    for net in tree.findall("nets/net"):
        name = net.attrib["name"]
        for node in net.findall("node"):
            key = (node.attrib["ref"], node.attrib["pin"])
            if key in nodes and nodes[key] != name:
                duplicates.append({"ref": key[0], "pad": key[1], "nets": sorted({nodes[key], name})})
            nodes[key] = name
    named = {k: v for k, v in nodes.items() if not v.startswith(UNNAMED_PREFIX)}
    refs = {c.attrib["ref"] for c in tree.findall("components/comp")}
    info = {"components": len(refs), "nodes": len(nodes), "named_nodes": len(named),
            "named_nets": len(set(named.values())), "tool": (tree.findtext("design/tool") or "").strip(),
            "source": (tree.findtext("design/source") or "").strip()}
    return named, refs, info, duplicates


def load_board(path: Path) -> tuple[dict, set, dict, list]:
    import pcbnew  # KiCad's bundled Python only

    board = pcbnew.LoadBoard(str(path))
    pads: dict = {}
    conflicts = []
    refs = set()
    pad_count = 0
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        refs.add(ref)
        for pad in fp.Pads():
            pad_count += 1
            number = pad.GetNumber()
            if not number:
                continue  # unnumbered mechanical pads carry no connection
            net = pad.GetNetname() or ""
            key = (ref, number)
            if key in pads and pads[key] != net:
                conflicts.append({"ref": ref, "pad": number, "nets": sorted({pads[key], net})})
            pads[key] = net
    named = {k: v for k, v in pads.items() if v and not v.startswith(UNNAMED_PREFIX)}
    info = {"footprints": len(refs), "pads": pad_count, "numbered_pads": len(pads), "named_pads": len(named),
            "named_nets": len(set(named.values())), "pcbnew_version": pcbnew.GetBuildVersion()}
    return named, refs, info, conflicts


def compare(a: dict, b: dict, a_name: str, b_name: str, a_refs: set, b_refs: set) -> dict:
    keys = sorted(set(a) | set(b))
    mismatches = [{"ref": r, "pad": p, a_name: a.get((r, p)), b_name: b.get((r, p))}
                  for r, p in keys if a.get((r, p)) != b.get((r, p))]
    return {
        "exact": not mismatches and a_refs == b_refs,
        "pads_compared": len(keys),
        "mismatches": len(mismatches),
        "only_in_" + a_name: sum(1 for m in mismatches if m[b_name] is None),
        "only_in_" + b_name: sum(1 for m in mismatches if m[a_name] is None),
        "different_net": sum(1 for m in mismatches if m[a_name] is not None and m[b_name] is not None),
        "components_equal": a_refs == b_refs,
        "components_only_in_" + a_name: sorted(a_refs - b_refs),
        "components_only_in_" + b_name: sorted(b_refs - a_refs),
        "mismatch_list": mismatches,
    }


def kicad_python() -> Path | None:
    from automation.setup.detect_kicad import find_kicad_cli

    cli = find_kicad_cli()
    if not cli:
        return None
    candidate = cli.parent / ("python.exe" if os.name == "nt" else "python3")
    return candidate if candidate.is_file() else None


def run(board: str, xml_path: Path, pcb_path: Path, output: Path) -> dict:
    cfg = BOARDS[board]
    model_path = EXAMPLE / "design" / f"circuit_{board}.json"
    expected, model_refs, model_info = load_model(model_path)
    result = {
        "schema_version": 1,
        "status": "in_progress",
        "board": board,
        "project": cfg["name"],
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "checker": "automation/verification/netlist_check_sic.py",
        "scope": "pad/net equality between model, schematic netlist and board only; hardware unqualified",
        "inputs": {"model": {"file": str(model_path), "sha256": sha(model_path), **model_info}},
        "problems": [],
    }
    if not xml_path.exists():
        result["inputs"]["schematic_netlist"] = {"file": str(xml_path), "exists": False}
        result["problems"].append(f"schematic netlist missing: {xml_path}")
        result["schematic_vs_model"] = None
        sch = sch_refs = None
    else:
        sch, sch_refs, sch_info, duplicates = load_xml(xml_path)
        result["inputs"]["schematic_netlist"] = {"file": str(xml_path), "sha256": sha(xml_path), "exists": True,
                                                  **sch_info, "conflicting_nodes": duplicates}
        result["schematic_vs_model"] = compare(sch, expected, "schematic", "model", sch_refs, model_refs)
        if duplicates:
            result["problems"].append(f"schematic netlist lists {len(duplicates)} pins under two nets")
        if not result["schematic_vs_model"]["exact"]:
            result["problems"].append("schematic netlist differs from the model")
    if not pcb_path.exists():
        result["inputs"]["board"] = {"file": str(pcb_path), "exists": False}
        result["board_vs_model"] = None
        result["board_vs_schematic"] = None
        result["problems"].append(f"board file missing: {pcb_path}")
        result["status"] = "board_missing"
    else:
        pads, pcb_refs, pcb_info, conflicts = load_board(pcb_path)
        result["inputs"]["board"] = {"file": str(pcb_path), "sha256": sha(pcb_path), "exists": True,
                                     **pcb_info, "conflicting_pads": conflicts}
        result["board_vs_model"] = compare(pads, expected, "board", "model", pcb_refs, model_refs)
        if conflicts:
            result["problems"].append(f"board has {len(conflicts)} pad numbers carrying two nets")
        if not result["board_vs_model"]["exact"]:
            result["problems"].append("board pad nets differ from the model")
        if sch is not None:
            result["board_vs_schematic"] = compare(pads, sch, "board", "schematic", pcb_refs, sch_refs)
            if not result["board_vs_schematic"]["exact"]:
                result["problems"].append("board pad nets differ from the schematic netlist")
        else:
            result["board_vs_schematic"] = None
    checks = [result.get("schematic_vs_model"), result.get("board_vs_model"), result.get("board_vs_schematic")]
    result["exact_match"] = all(c is not None and c["exact"] for c in checks) and not result["problems"]
    if result["status"] != "board_missing":
        result["status"] = "passed" if result["exact_match"] else "failed"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--board", choices=sorted(BOARDS), required=True)
    parser.add_argument("--xml", type=Path, help="kicad-cli XML netlist (default manufacturing/<board_dir>/netlist.xml)")
    parser.add_argument("--pcb", type=Path, help="board file (default kicad/<board_dir>/<name>.kicad_pcb)")
    parser.add_argument("--output", type=Path, help="default verification/netlist_check_<board>.json")
    parser.add_argument("--no-reexec", action="store_true", help="internal: do not re-execute under KiCad Python")
    args = parser.parse_args(argv)
    cfg = BOARDS[args.board]
    xml_path = args.xml or EXAMPLE / "manufacturing" / cfg["dir"] / "netlist.xml"
    pcb_path = args.pcb or EXAMPLE / "kicad" / cfg["dir"] / f"{cfg['name']}.kicad_pcb"
    output = args.output or EXAMPLE / "verification" / f"netlist_check_{args.board}.json"
    if pcb_path.exists() and not args.no_reexec:
        try:
            import pcbnew  # noqa: F401
        except ImportError:
            python = kicad_python()
            if not python:
                print("pcbnew unavailable and no KiCad Python found", file=sys.stderr)
                return 2
            cmd = [str(python), str(Path(__file__).resolve()), "--board", args.board, "--xml", str(xml_path),
                   "--pcb", str(pcb_path), "--output", str(output), "--no-reexec"]
            return subprocess.call(cmd, cwd=str(ROOT))
    result = run(args.board, xml_path.resolve(), pcb_path.resolve(), output.resolve())
    summary = {k: v for k, v in result.items() if k != "inputs"}
    for key in ("schematic_vs_model", "board_vs_model", "board_vs_schematic"):
        if summary.get(key):
            summary[key] = {k: v for k, v in summary[key].items() if k != "mismatch_list"}
    print(json.dumps(summary, indent=2))
    return 0 if result["exact_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
