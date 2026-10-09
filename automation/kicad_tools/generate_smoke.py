"""Generate a real three-net divider with placement, tracks, vias and ground zone.

Run with KiCad's bundled Python. This uses its shipped PCB Python bindings as a
headless fallback; official CLI handles all verification and exports.
"""

from __future__ import annotations

import argparse
import json
import shutil
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from automation.kicad_tools.native_schematic import Schematic, extract_symbol
from automation.setup.detect_kicad import find_kicad_cli


def generate(output: Path) -> None:
    import pcbnew as pcb

    cli = find_kicad_cli()
    if not cli:
        raise FileNotFoundError("KiCad CLI not available")
    # Windows bundled layout; other platforms can provide the explicit data root.
    data = Path(__import__("os").environ.get("AIPE_KICAD_DATA", str(cli.parent.parent / "share/kicad")))
    output.mkdir(parents=True, exist_ok=True)
    library_dir = output / "libraries"
    library_dir.mkdir(exist_ok=True)
    resistor = extract_symbol(data / "symbols/Device.kicad_sym", "R")
    connector = extract_symbol(data / "symbols/Connector_Generic.kicad_sym", "Conn_01x03")
    for name, definition in (("Device", resistor), ("Connector_Generic", connector)):
        (library_dir / f"{name}.kicad_sym").write_text(
            f'(kicad_symbol_lib (version 20250114) (generator "aipe") {definition})\n', encoding="utf-8")
    (output / "sym-lib-table").write_text('''(sym_lib_table (version 7)
      (lib (name "Device") (type "KiCad") (uri "${KIPRJMOD}/libraries/Device.kicad_sym") (options "") (descr "KiCad library subset"))
      (lib (name "Connector_Generic") (type "KiCad") (uri "${KIPRJMOD}/libraries/Connector_Generic.kicad_sym") (options "") (descr "KiCad library subset")))
''', encoding="utf-8")
    footprints = {"R": ("Resistor_SMD", "R_0805_2012Metric"),
                  "J": ("Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical")}
    table = ['(fp_lib_table (version 7)']
    for lib, name in footprints.values():
        target = library_dir / f"{lib}.pretty"
        target.mkdir(exist_ok=True)
        destination = target / f"{name}.kicad_mod"
        if destination.exists():
            destination.chmod(stat.S_IREAD | stat.S_IWRITE)
        shutil.copyfile(data / f"footprints/{lib}.pretty/{name}.kicad_mod", destination)
        table.append(f'(lib (name "{lib}") (type "KiCad") (uri "${{KIPRJMOD}}/libraries/{lib}.pretty") (options "") (descr "KiCad library subset"))')
    (output / "fp-lib-table").write_text("\n".join(table) + ")\n", encoding="utf-8")
    ids = {key: ":".join(value) for key, value in footprints.items()}

    sch = Schematic("AIPE_Smoke", "AIPE automation smoke test - passive divider")
    p1 = sch.add_symbol("Device:R", resistor, "R1", "10k", ids["R"], 101.6, 63.5)
    p2 = sch.add_symbol("Device:R", resistor, "R2", "10k", ids["R"], 101.6, 88.9)
    pj = sch.add_symbol("Connector_Generic:Conn_01x03", connector, "J1", "VIN_VOUT_GND", ids["J"], 63.5, 76.2)
    # Stubbed net labels keep the small schematic uncluttered and all pins connected.
    for points, pinmap in ((p1, {"1": "VIN", "2": "VOUT"}),
                            (p2, {"1": "VOUT", "2": "GND"}),
                            (pj, {"1": "VIN", "2": "VOUT", "3": "GND"})):
        for number, net in pinmap.items():
            point = points[number]
            end = (round(point[0] - 7.62, 4), round(point[1], 4))
            sch.wire(point, end)
            sch.label(net, end)
    sch.write(output / "AIPE_Smoke.kicad_sch")
    (output / "AIPE_Smoke.kicad_pro").write_text(json.dumps({
        "meta": {"filename": "AIPE_Smoke.kicad_pro", "version": 1},
        "net_settings": {"classes": [{"name": "Default", "clearance": 0.2,
            "track_width": 0.3, "via_diameter": 0.8, "via_drill": 0.4}], "version": 4},
    }, indent=2) + "\n", encoding="utf-8")

    board = pcb.BOARD()
    board.SetCopperLayerCount(2)
    board.GetDesignSettings().SetBoardThickness(pcb.FromMM(1.6))
    nets = {}
    for name in ("VIN", "VOUT", "GND"):
        nets[name] = pcb.NETINFO_ITEM(board, "/" + name)
        board.Add(nets[name])

    def point(x, y):
        return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))

    pads = {}
    for ref, kind, x, y, value, pinmap in (
        ("J1", "J", 25, 25, "VIN_VOUT_GND", {"1": "VIN", "2": "VOUT", "3": "GND"}),
        ("R1", "R", 35, 25, "10k", {"1": "VIN", "2": "VOUT"}),
        ("R2", "R", 35, 33, "10k", {"1": "VOUT", "2": "GND"}),
    ):
        lib, name = footprints[kind]
        fp = pcb.FootprintLoad(str(library_dir / f"{lib}.pretty"), name)
        if not fp:
            raise RuntimeError(f"Cannot load footprint {name}")
        fp.SetFPID(pcb.LIB_ID(lib, name))
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetPosition(point(x, y))
        fp.SetPath(pcb.KIID_PATH(f"/{sch.root_uuid}/{sch.references[ref]}"))
        board.Add(fp)
        for pad in fp.Pads():
            number = pad.GetNumber()
            pad.SetNet(nets[pinmap[number]])
            pads[(ref, number)] = pad.GetPosition()

    def track(a, b, net, layer=pcb.F_Cu):
        item = pcb.PCB_TRACK(board)
        item.SetStart(a)
        item.SetEnd(b)
        item.SetLayer(layer)
        item.SetWidth(pcb.FromMM(0.3))
        item.SetNet(nets[net])
        board.Add(item)

    track(pads["J1", "1"], pads["R1", "1"], "VIN")
    track(pads["R1", "2"], point(39, 25), "VOUT")
    track(point(39, 25), point(39, 29), "VOUT")
    track(point(39, 29), point(33, 29), "VOUT")
    track(point(33, 29), pads["R2", "1"], "VOUT")
    track(pads["J1", "2"], point(29, 27.54), "VOUT")
    track(point(29, 27.54), point(30.46, 29), "VOUT")
    track(point(30.46, 29), point(33, 29), "VOUT")
    via_pos = point(39, 33)
    track(pads["R2", "2"], via_pos, "GND")
    via = pcb.PCB_VIA(board)
    via.SetPosition(via_pos)
    via.SetWidth(pcb.FromMM(0.8))
    via.SetDrill(pcb.FromMM(0.4))
    via.SetLayerPair(pcb.F_Cu, pcb.B_Cu)
    via.SetViaType(pcb.VIATYPE_THROUGH)
    via.SetNet(nets["GND"])
    board.Add(via)
    track(via_pos, point(29, 33), "GND", pcb.B_Cu)
    track(point(29, 33), pads["J1", "3"], "GND", pcb.B_Cu)

    for a, b in (((20, 20), (45, 20)), ((45, 20), (45, 38)),
                 ((45, 38), (20, 38)), ((20, 38), (20, 20))):
        edge = pcb.PCB_SHAPE(board)
        edge.SetShape(pcb.SHAPE_T_SEGMENT)
        edge.SetStart(point(*a))
        edge.SetEnd(point(*b))
        edge.SetLayer(pcb.Edge_Cuts)
        edge.SetWidth(pcb.FromMM(0.05))
        board.Add(edge)
    zone = pcb.ZONE(board)
    zone.SetLayer(pcb.B_Cu)
    zone.SetNet(nets["GND"])
    zone.SetLocalClearance(pcb.FromMM(0.25))
    zone.SetThermalReliefGap(pcb.FromMM(0.3))
    zone.SetThermalReliefSpokeWidth(pcb.FromMM(0.3))
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in ((20.5, 20.5), (44.5, 20.5), (44.5, 37.5), (20.5, 37.5)):
        outline.Append(pcb.FromMM(x), pcb.FromMM(y))
    board.Add(zone)
    board.BuildConnectivity()
    pcb.ZONE_FILLER(board).Fill(board.Zones())
    pcb.SaveBoard(str(output / "AIPE_Smoke.kicad_pcb"), board)
    print(f"Generated smoke source at {output}; real KiCad checks are still required.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "examples/automation-smoke/kicad")
    generate(parser.parse_args().output.resolve())
