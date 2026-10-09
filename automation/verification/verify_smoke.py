"""Check real smoke reports, explicit net connectivity, export hashes and source."""

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def verify() -> dict:
    root = ROOT / "examples/automation-smoke"
    evidence = {}
    for kind in ("erc", "drc"):
        candidates = sorted((root / "verification").glob(f"*-{kind}-*/run.json"))
        if not candidates:
            raise ValueError(f"No {kind} run exists")
        manifest = json.loads(candidates[-1].read_text(encoding="utf-8"))
        if manifest["status"] != "passed" or manifest["wrapper_exit_code"] != 0:
            raise ValueError(f"Latest {kind} run did not pass")
        source = root / "kicad" / ("AIPE_Smoke.kicad_sch" if kind == "erc" else "AIPE_Smoke.kicad_pcb")
        if hashlib.sha256(source.read_bytes()).hexdigest() != manifest["source_sha256"]:
            raise ValueError(f"Source changed since {kind}")
        evidence[kind] = candidates[-1].relative_to(ROOT).as_posix()
    exports = root / "outputs"
    manifest = json.loads((exports / "export-manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "passed" or len(manifest["commands"]) != 11:
        raise ValueError("Exports incomplete")
    for name, expected in manifest["artifacts"].items():
        data = (exports / name).read_bytes()
        if len(data) != expected["bytes"] or hashlib.sha256(data).hexdigest() != expected["sha256"]:
            raise ValueError(f"Export changed or corrupted: {name}")
    netlist = ET.parse(exports / "netlist.xml")
    nets = {net.attrib["name"]: sorted((n.attrib["ref"], n.attrib["pin"]) for n in net.findall("node"))
            for net in netlist.findall("./nets/net")}
    expected_nets = {"/VIN": [("J1", "1"), ("R1", "1")],
                     "/VOUT": [("J1", "2"), ("R1", "2"), ("R2", "1")],
                     "/GND": [("J1", "3"), ("R2", "2")]}
    if nets != expected_nets:
        raise ValueError(f"Unexpected smoke connectivity: {nets}")
    evidence.update(status="passed", exact_connectivity=True,
                    export_commands=len(manifest["commands"]), exported_files=len(manifest["artifacts"]),
                    kicad_version="10.0.7", scope="automation smoke only; not the 1 kW converter")
    (root / "verification/smoke-result.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return evidence


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
